/**
 * Đọc lời bình bằng giọng Gemini, gọi thẳng từ trình duyệt.
 *
 * Key TTS KHÔNG đi qua máy chủ nào — kể cả ở chế độ Local. Khác với key đánh cờ (bản local
 * gửi lên máy chủ Flask), phần đọc tiếng gọi trực tiếp tới Google.
 *
 * CHƯA KIỂM CHỨNG bằng key thật. Định dạng phản hồi (`audio/l16`) lấy từ lần đo trước đó,
 * phần bọc WAV kiểm bằng dữ liệu tổng hợp.
 */

import { getKey } from "./key-vault.js";

const BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models";

// Giọng dựng sẵn của Google. Đều đa ngôn ngữ nên đọc tiếng Việt được.
export const VOICES = ["Kore", "Puck", "Charon", "Fenrir", "Aoede", "Leda", "Orus", "Zephyr"];

let current = null;      // Audio đang phát
let totalCostUsd = 0;    // chi phí đọc luỹ kế của phiên

export function isAvailable() {
    return Boolean(getKey("gemini"));
}

export function sessionCostUsd() {
    return totalCostUsd;
}

export function resetCost() {
    totalCostUsd = 0;
}

export function isSpeaking() {
    return current !== null;
}

export function stop() {
    if (!current) return;
    current.pause();
    URL.revokeObjectURL(current.src);
    current = null;
}

/**
 * Đọc một câu bằng giọng Gemini.
 *
 * Trả { ok, error, costUsd, skipped }. Không bao giờ ném lỗi: mất tiếng không được phép làm
 * hỏng trận đang chạy.
 *
 * ĐANG ĐỌC THÌ BỎ QUA câu mới, không xếp hàng. Trận cờ chạy tiếp bất kể tiếng đọc; dồn hàng
 * đợi sẽ khiến lời bình tụt lại 3-4 nước so với bàn cờ, vừa vô nghĩa vừa tốn thêm tiền cho
 * mỗi câu không ai cần nghe nữa.
 */
export async function speak(text, { model, voice = "Kore", signal } = {}) {
    if (!text) return { ok: false, skipped: true };
    if (current) return { ok: false, skipped: true };

    const apiKey = getKey("gemini");
    if (!apiKey) return { ok: false, error: "Chưa có API key Gemini" };

    let payload;
    try {
        const response = await fetch(`${BASE_URL}/${model.model_id}:generateContent`, {
            method: "POST",
            headers: { "content-type": "application/json", "x-goog-api-key": apiKey },
            body: JSON.stringify({
                contents: [{ parts: [{ text }] }],
                generationConfig: {
                    responseModalities: ["AUDIO"],
                    speechConfig: {
                        voiceConfig: { prebuiltVoiceConfig: { voiceName: voice } },
                    },
                },
            }),
            signal,
        });
        payload = await response.json().catch(() => null);
        if (!response.ok) {
            return { ok: false, error: payload?.error?.message ?? `HTTP ${response.status}` };
        }
    } catch (error) {
        return { ok: false, error: `Không gọi được API đọc tiếng: ${error.message}` };
    }

    const inline = payload?.candidates?.[0]?.content?.parts?.find((p) => p.inlineData)?.inlineData;
    if (!inline?.data) {
        return { ok: false, error: "Phản hồi không có dữ liệu âm thanh" };
    }

    const usage = payload.usageMetadata ?? {};
    const costUsd = estimateCost(model, usage);
    if (costUsd !== null) totalCostUsd += costUsd;

    try {
        await play(pcmToWav(base64ToBytes(inline.data), parseAudioMime(inline.mimeType)));
    } catch (error) {
        return { ok: false, error: `Không phát được âm thanh: ${error.message}`, costUsd };
    }
    return { ok: true, costUsd };
}

function estimateCost(model, usage) {
    if (model.input_price == null || model.output_price == null) return null;
    const tokensIn = usage.promptTokenCount ?? 0;
    // Token âm thanh nằm ở candidatesTokenCount và là phần đắt nhất
    const tokensOut = usage.candidatesTokenCount ?? 0;
    return (tokensIn * model.input_price + tokensOut * model.output_price) / 1e6;
}

/**
 * Đọc thông số từ mimeType, ví dụ `audio/l16; rate=24000; channels=1`.
 *
 * ĐỌC ĐỘNG chứ không hardcode 24000: Google có thể đổi tần số lấy mẫu, mà đoán sai tần số
 * thì tiếng vẫn phát được — chỉ là nhanh hoặc chậm bất thường như băng tua. Kiểu lỗi đó rất
 * khó lần ra vì không có thông báo nào.
 */
export function parseAudioMime(mimeType) {
    const text = mimeType ?? "";
    const rate = /rate=(\d+)/i.exec(text);
    const channels = /channels=(\d+)/i.exec(text);
    const bits = /l(\d+)/i.exec(text.split(";")[0] ?? "");
    return {
        sampleRate: rate ? Number(rate[1]) : 24000,
        channels: channels ? Number(channels[1]) : 1,
        bitsPerSample: bits ? Number(bits[1]) : 16,
    };
}

export function base64ToBytes(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes;
}

/**
 * Bọc PCM thô thành file WAV.
 *
 * Gemini trả `audio/l16` — mẫu PCM trần, KHÔNG có header. Trình duyệt không phát trực tiếp
 * được: `new Audio()` với dữ liệu này chỉ im lặng, không báo lỗi gì. Phải tự dựng header
 * RIFF/WAVE 44 byte rồi nối vào trước.
 */
export function pcmToWav(pcmBytes, { sampleRate, channels, bitsPerSample }) {
    const bytesPerSample = bitsPerSample / 8;
    const blockAlign = channels * bytesPerSample;
    const buffer = new ArrayBuffer(44 + pcmBytes.length);
    const view = new DataView(buffer);

    const writeText = (offset, text) => {
        for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
    };

    writeText(0, "RIFF");
    view.setUint32(4, 36 + pcmBytes.length, true);   // kích thước còn lại của file
    writeText(8, "WAVE");
    writeText(12, "fmt ");
    view.setUint32(16, 16, true);                    // độ dài khối fmt
    view.setUint16(20, 1, true);                     // 1 = PCM không nén
    view.setUint16(22, channels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * blockAlign, true);  // byte mỗi giây
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    writeText(36, "data");
    view.setUint32(40, pcmBytes.length, true);
    new Uint8Array(buffer, 44).set(pcmBytes);

    return new Blob([buffer], { type: "audio/wav" });
}

function play(wavBlob) {
    return new Promise((resolve, reject) => {
        const url = URL.createObjectURL(wavBlob);
        const audio = new Audio(url);
        current = audio;
        const finish = (fail) => {
            if (current === audio) current = null;
            URL.revokeObjectURL(url);
            fail ? reject(new Error("Trình duyệt từ chối phát")) : resolve();
        };
        audio.onended = () => finish(false);
        audio.onerror = () => finish(true);
        audio.play().catch(() => finish(true));
    });
}
