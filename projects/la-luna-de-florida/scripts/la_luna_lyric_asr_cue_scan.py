#!/usr/bin/env python3
"""Whisper word-time estimates for La Luna. Evidence only; never script lock."""
import argparse,hashlib,json,re,unicodedata,wave
from pathlib import Path
from difflib import SequenceMatcher

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()

def norm(s):
 s="".join(c for c in unicodedata.normalize("NFD",str(s).lower()) if unicodedata.category(c)!="Mn")
 return re.sub(r"[^a-z0-9 ]+"," ",s).strip()

def main():
 a=argparse.ArgumentParser()
 a.add_argument("--wav",required=True)
 a.add_argument("--lyrics",required=True)
 a.add_argument("--out",required=True)
 x=a.parse_args(); w=Path(x.wav); l=Path(x.lyrics); out=Path(x.out)
 out.mkdir(parents=True,exist_ok=True)
 expected="1a4bffef36930b504423d2653faff4cc5bfd9a15d44bdcf1083b27fbb0db1c10"
 if sha(w)!=expected:raise SystemExit("REFUSE: original WAV hash mismatch")
 with wave.open(str(w)) as f:
  duration=f.getnframes()/f.getframerate();rate=f.getframerate();channels=f.getnchannels()
 if rate!=48000 or channels!=2 or abs(duration-321.16)>.02:raise SystemExit("REFUSE: WAV format or duration mismatch")
 from faster_whisper import WhisperModel
 model=WhisperModel("base",device="cpu",compute_type="int8",cpu_threads=4)
 raw,info=model.transcribe(str(w),language="es",beam_size=5,word_timestamps=True,vad_filter=False,condition_on_previous_text=False)
 segs=[];words=[]
 for i,s in enumerate(raw):
  segs.append(dict(i=i,start_seconds=round(s.start,3),end_seconds=round(s.end,3),text=s.text.strip(),avg_logprob=round(s.avg_logprob,4)))
  for v in (s.words or []):
   words.append(dict(start_seconds=round(v.start,3),end_seconds=round(v.end,3),text=v.word.strip(),probability=round(v.probability,3)))
 if not words:raise SystemExit("No word-level timestamps produced")
 lines=[];section=""
 for line in l.read_text(encoding="utf-8").splitlines():
  line=line.strip()
  if not line:continue
  if line.startswith("[") and line.endswith("]"):
   section=line[1:-1];continue
  lines.append(dict(section=section,text=line))
 cursor=0
 for item in lines:
  target=norm(item["text"]).split();best=(0.0,None,None)
  for start in range(cursor,min(len(words),cursor+45)):
   for size in range(max(2,len(target)-3),min(len(target)+5,16)+1):
    end=min(len(words),start+size)
    if end-start<2:continue
    score=SequenceMatcher(None,norm(item["text"]),norm(" ".join(v["text"] for v in words[start:end]))).ratio()
    if score>best[0]:best=score,start,end
  score,start,end=best
  if score>=.63:
   item.update(status="ASR_ESTIMATE_NEEDS_AUDIBLE_VERIFICATION",score=round(score,4),start_seconds_estimated=words[start]["start_seconds"],end_seconds_estimated=words[end-1]["end_seconds"],matching_transcript=" ".join(v["text"] for v in words[start:end]))
   cursor=end
  else:item.update(status="UNMATCHED_ASR",best_score=round(score,4))
 result=dict(schema="aivideoedit.la-luna-word-cue-ASR-candidate.v1",authority="evidence_only",source_wav_sha256=expected,source_duration_seconds=duration,original_lyrics_sha256=sha(l),model="faster-whisper base int8 CPU",model_reproducibility_note="Candidate model download snapshot revision not yet independently pinned",results_are_verified_lyric_boundaries=False,script_locked=False,release_approved=False,transcript_segments=segs,asr_word_estimates=words,canonical_lyric_lines_estimates=lines)
 (out/"LYRIC_CUE_ASR_CANDIDATE.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
 (out/"LYRIC_CUE_DIRECTOR_TIMING_NOTES.md").write_text("# La Luna — ASR candidate only\n\nOriginal WAV SHA verified. Independent Spanish Whisper ASR estimates; errors possible. Each estimate needs audible verification. ONNX beats are not vocal line times. SCRIPT remains unlocked.\n\n"+"\n".join("- "+v["section"]+": "+v["text"]+" — "+str(v.get("start_seconds_estimated","?"))+"–"+str(v.get("end_seconds_estimated","?"))+"s ("+v["status"]+")" for v in lines)+"\n")
 print(json.dumps(dict(wav_sha256=expected,duration_s=duration,recognized_segments=len(segs),words=len(words),lyric_lines=len(lines),estimated_lines=sum(z["status"].startswith("ASR_ESTIMATE") for z in lines),unmatched_lines=sum(z["status"]=="UNMATCHED_ASR" for z in lines),status="ASR_CANDIDATE_NEEDS_AUDIBLE_REVIEW"),indent=2))

if __name__=="__main__":main()
