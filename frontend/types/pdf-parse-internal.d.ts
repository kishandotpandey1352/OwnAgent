declare module "pdf-parse/lib/pdf-parse.js" {
  type PdfParseResult = {
    text?: string;
    numpages?: number;
  };

  type PdfParseFunction = (buffer: Buffer) => Promise<PdfParseResult>;

  const pdfParse: PdfParseFunction;
  export default pdfParse;
}