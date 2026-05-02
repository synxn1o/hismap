export const palettes: Record<string, string[]> = {
  warm: [
    "#E63946", "#F4A261", "#2A9D8F", "#264653",
    "#E9C46A", "#606C38", "#DDA15E", "#BC6C25",
  ],
  ocean: [
    "#0077B6", "#00B4D8", "#90E0EF", "#CAF0F8",
    "#023E8A", "#48CAE4", "#ADE8F4", "#03045E",
  ],
  earth: [
    "#6B4226", "#C68642", "#8B6914", "#DAA520",
    "#556B2F", "#8FBC8F", "#B22222", "#CD853F",
  ],
};

export function getBookColor(bookId: number, palette: string[] = palettes.warm): string {
  return palette[bookId % palette.length];
}
