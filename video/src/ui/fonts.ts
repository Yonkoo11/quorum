// The site's own fonts, loaded from public/fonts before any frame renders (no CDN, no Google Fonts).
import { continueRender, delayRender, staticFile } from "remotion";

export const DISPLAY = "Archivo Black";
export const SANS = "IBM Plex Sans";

const handle = delayRender("brand fonts");
Promise.all([
  new FontFace(DISPLAY, `url(${staticFile("fonts/ArchivoBlack-Regular.woff2")}) format("woff2")`, { weight: "400" }).load(),
  new FontFace(SANS, `url(${staticFile("fonts/IBMPlexSans-Medium.woff2")}) format("woff2")`, { weight: "500" }).load(),
])
  .then((faces) => {
    faces.forEach((f) => (document.fonts as unknown as { add(face: FontFace): void }).add(f));
    continueRender(handle);
  })
  .catch((err) => {
    console.error("brand fonts failed to load", err);
    continueRender(handle);
  });
