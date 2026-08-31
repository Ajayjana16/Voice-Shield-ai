import { useRef, useState } from "react";

export function useWavRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const contextRef = useRef(null);
  const streamRef = useRef(null);

  async function record(seconds = 4) {
    setIsRecording(true);
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    const context = new AudioContext();
    contextRef.current = context;
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    const chunks = [];

    processor.onaudioprocess = (event) => {
      chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    };

    source.connect(processor);
    processor.connect(context.destination);

    await new Promise((resolve) => window.setTimeout(resolve, seconds * 1000));

    processor.disconnect();
    source.disconnect();
    stream.getTracks().forEach((track) => track.stop());
    await context.close();
    setIsRecording(false);

    const samples = mergeChunks(chunks);
    const wav = encodeWav(samples, context.sampleRate);
    return new File([wav], `microphone-${Date.now()}.wav`, { type: "audio/wav" });
  }

  return { isRecording, record };
}

function mergeChunks(chunks) {
  const length = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const output = new Float32Array(length);
  let offset = 0;
  chunks.forEach((chunk) => {
    output.set(chunk, offset);
    offset += chunk.length;
  });
  return output;
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, "data");
  view.setUint32(40, samples.length * 2, true);
  let offset = 44;
  samples.forEach((sample) => {
    const clipped = Math.max(-1, Math.min(1, sample));
    view.setInt16(offset, clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff, true);
    offset += 2;
  });
  return buffer;
}

function writeString(view, offset, value) {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index));
  }
}
