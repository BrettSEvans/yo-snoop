// MAIN world, document_start: supplies Snoop's mic and camera to Meet.
(() => {
  const TAG = "snoop-spike";
  const ac = new AudioContext({sampleRate: 24000});
  const dest = ac.createMediaStreamDestination();
  let sources = [], playHead = 0, cardText = "Snoop";

  const canvas = document.createElement("canvas");
  canvas.width = 1280; canvas.height = 720;
  const g = canvas.getContext("2d");
  function drawCard() {
    g.fillStyle = "#111"; g.fillRect(0, 0, 1280, 720);
    g.fillStyle = "#fff"; g.font = "bold 72px sans-serif"; g.textAlign = "center";
    g.fillText(cardText, 640, 380);
  }
  drawCard(); setInterval(drawCard, 1000);
  const cardTrack = canvas.captureStream(5).getVideoTracks()[0];

  function playPcm(b64, rate) {
    const bytes = Uint8Array.from(atob(b64), (ch) => ch.charCodeAt(0));
    const samples = new Int16Array(bytes.buffer);
    const buf = ac.createBuffer(1, samples.length, rate);
    const out = buf.getChannelData(0);
    for (let i = 0; i < samples.length; i++) out[i] = samples[i] / 32768;
    const src = ac.createBufferSource();
    src.buffer = buf; src.connect(dest);
    playHead = Math.max(playHead, ac.currentTime);
    src.start(playHead); playHead += buf.duration;
    sources.push(src); src.onended = () => { sources = sources.filter((s) => s !== src); };
  }
  function stopAll() { sources.forEach((s) => { try { s.stop(); } catch (e) {} }); sources = []; playHead = ac.currentTime; }

  window.addEventListener("message", (e) => {
    if (e.source !== window || e.data?.tag !== TAG || e.data.dir !== "to-page") return;
    const m = e.data.msg;
    if (m.type === "audio") { ac.resume(); playPcm(m.pcm_b64, m.rate); }
    else if (m.type === "stop") stopAll();
    else if (m.type === "card") cardText = m.text;
  });

  // P2b: the meeting audio this seat receives goes to the host's Mac for the wake/stop checks.
  // Remote audio tracks are mixed at 16 kHz and sent in ~0.26 s chunks; nothing is stored here.
  const listenCtx = new AudioContext({sampleRate: 16000});
  const mix = listenCtx.createGain();
  const tap = listenCtx.createScriptProcessor(4096, 1, 1);
  mix.connect(tap); tap.connect(listenCtx.destination);  // the tap outputs silence; Meet plays the audio itself
  tap.onaudioprocess = (e) => {
    const f = e.inputBuffer.getChannelData(0);
    e.outputBuffer.getChannelData(0).fill(0);
    const pcm = new Int16Array(f.length);
    for (let i = 0; i < f.length; i++) pcm[i] = Math.max(-1, Math.min(1, f[i])) * 32767;
    const bytes = new Uint8Array(pcm.buffer);
    let bin = "";
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    window.postMessage({tag: TAG, dir: "to-ext", msg: {type: "meet_audio", pcm_b64: btoa(bin), rate: 16000}}, location.origin);
  };
  const RealPC = window.RTCPeerConnection;
  window.RTCPeerConnection = function (...args) {
    const pc = new RealPC(...args);
    pc.addEventListener("track", (ev) => {
      if (ev.track.kind !== "audio") return;
      listenCtx.resume();
      listenCtx.createMediaStreamSource(new MediaStream([ev.track])).connect(mix);
    });
    return pc;
  };
  window.RTCPeerConnection.prototype = RealPC.prototype;
  Object.setPrototypeOf(window.RTCPeerConnection, RealPC);  // keep static methods (generateCertificate)

  const real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  navigator.mediaDevices.getUserMedia = async (constraints = {}) => {
    const tracks = [];
    if (constraints.audio) tracks.push(dest.stream.getAudioTracks()[0].clone());
    if (constraints.video) tracks.push(cardTrack.clone());
    if (!tracks.length) return real(constraints);
    return new MediaStream(tracks);
  };
})();
