
## Decision: UI launch clip uses the site's brand, not the skill's archetype theme (2026-09-12)
**Recommendation:** paper #f3eee4, ink #121212, green #3fb950; Archivo Black + IBM Plex Sans from docs/fonts; no orbs, no glass, no glow.
**Rationale:** the skill's dark/Inter/orb defaults are the template the user's no-slop rules reject; the product is a cream-and-ink site and the clip is that site moving.
**Override:** src/ui/constants.ts COLORS and fonts.
**Affected files:** src/ui/*.

## Decision: silent, on-screen titles only
**Recommendation:** no narration, no music. Titles in the brand type carry the beats; X autoplays muted.
**Rationale:** a UI launch is watched muted; adding TTS would add the one thing that reads as generated.
**Override:** record a voice memo, add Mode B audio per scene, run Whisper for subtitles.
**Affected files:** src/ui/UiLaunch.tsx (add SceneAudio), constants SUBTITLES.
