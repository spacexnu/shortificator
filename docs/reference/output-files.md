# Output Files

For an input named `my_video.mp4`, shortificator writes:

| File | Content |
| --- | --- |
| `my_video_transcript.json` | full transcript with word timestamps |
| `my_video_candidates.json` | LLM candidates with score and reason |
| `my_video_short_01.mp4` | first rendered Short |
| `my_video_short_02.mp4` | second rendered Short |
| `my_video_subtitled.mp4` | full source video with burned subtitles when `--subtitles-only` is enabled |
| `my_video.srt` | full-source subtitles when `--srt` is enabled |
| `my_video_short_01.srt` | clip-relative subtitles when `--srt` is enabled |

Generated videos, transcripts, candidates, SRT files, downloaded videos, and models should not be committed.
