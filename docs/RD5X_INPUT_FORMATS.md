# Noritsu RD5X input and raster formats

This separates the scanner/film raster ABI from the conventional file path
used by the working headless demonstration.

## Recommended headless input

Use CmdID 19 (ProcessDoFormatConv) with an ordinary BMP source and BMP
destination. This route is verified on the Windows 10 VM and does not require
scanner calibration data or a synthetic NKC_IMAGE_IN_FILE raster.

The bundled decoder path recognizes more conventional formats, but the exact
minimal command proven end to end is:

~~~text
32-bpp BMP file -> CmdID 19 -> 24-bpp BMP file
~~~

The deterministic test input is 64 by 48 pixels and 12,342 bytes. The engine
writes a distinct 64 by 48, 24-bpp, 9,270-byte BMP.

## Conventional file dispatcher

ImgCorrectDLL.dll identifies the source extension in sub_101fbb00 at
0x101fbb00, using the table at 0x102a68b0. CmdID 19 reaches
CICCSImgOperationList::DoChangeFormatCImgConvertThread at 0x101aa100.
Non-RAW sources go through CImgConvertMultiCtrl::Convert at 0x101f8eb0.

The bundled ImageDataProc\PlugIn configuration and decoder DLLs substantiate:

- BMP
- DCX and PCX
- FPX
- JPG, JPE, JPEG, and JFIF
- PCD
- PIC, PCT, and PICT
- PNG
- PSD
- TGA and TARGA
- TIF and TIFF

Additional built-in extension-table entries are:

| Extension | Internal format |
| --- | ---: |
| RAW | 14 |
| HDP, WDP | 15 |
| NKCDCRAW | 16 |
| DNG | 18 |

GIF has an internal display enum but no extension entry or bundled plug-in in
this installation, so it is not listed as accepted.

For format 14 (.RAW), the format-conversion worker calls
CImgConvertMultiCtrl::ConvertFromRaw at 0x101fa4d0. It supplies explicit
width, height, three channels, and either 24 or 48 total bits based on the
source bit-depth field. This .RAW path is not the same ABI as
NKC_IMAGE_IN_FILE below.

Camera raw has a separate metadata-aware route:

- DoInitForDCRaw, RVA 0x138240
- DoUnifyProcForDCRaw(NKC_IMAGE_IN_FILE*), RVA 0x13b5e0
- DCRaw_JudgeMain, RVA 0x137000

It is unnecessary for the working BMP demonstration.

## Destination caveat

The engine contains JPEG-writing code, but a minimal CmdID 19 request with a
.jpg DstImg failed destination validation with HRESULT 0x80040991. The same
request with a .bmp DstImg succeeded. That means JPEG output needs additional
format metadata or another command shape; it does not establish that JPEG
writing is absent. The supplied driver therefore requires a .bmp destination.

## NKC_IMAGE_IN_FILE ABI

The film file overload receives a packed 38-byte, 32-bit in-memory descriptor.
It is not an on-disk header. ImgCorrectDLL.dll constructs it at
0x101a8ce2 through 0x101a8dba and calls the file overload of
DoInputProcForFilm through IAT slot 0x102925d4.

~~~c
#pragma pack(push, 2)
typedef struct NKC_IMAGE_IN_FILE {
    HANDLE   src;          // +0x00: 32-bit Windows file handle
    uint32_t srcOffset;    // +0x04: byte offset to raster
    uint16_t srcType;      // +0x08: 0..3
    int32_t  srcWidth;     // +0x0A
    int32_t  srcHeight;    // +0x0E
    uint16_t zero;         // +0x12: wrapper explicitly writes zero

    HANDLE   dst;          // +0x14
    uint32_t dstOffset;    // +0x18
    uint16_t dstType;      // +0x1C
    int32_t  dstWidth;     // +0x1E
    int32_t  dstHeight;    // +0x22
} NKC_IMAGE_IN_FILE;       // 0x26 / 38 bytes
#pragma pack(pop)
~~~

The handle interpretation is confirmed by NkcIBaseLib!ReadFileX wrapping
Windows ReadFile. Width and height must each be between 1 and 32,000; see
UniRdImgLib!DoInputProcForFilm at 0x1003a840 and its checks at
0x1003a9eb through 0x1003aa1a.

## Film raster type values

UniRdBaseLib!CreateParam at 0x10025ac0 maps the type values:

| Type | Raster representation | Exact row stride |
| ---: | --- | ---: |
| 0 | 3 slots × 8-bit BMP/DIB raster | align4(width × 3) |
| 1 | 4 slots × 8-bit BMP/DIB raster | width × 4 |
| 2 | Headerless 3 slots × 16-bit raw | width × 6 |
| 3 | Headerless 4 slots × 16-bit raw | width × 8 |

For types 0 and 1, CImageCtrlIO::SchDIBHeader at 0x10007890 searches up to the
first 1 MiB for the literal BM signature, then applies srcOffset. It does not
parse the BMP bfOffBits member. A conventional BMP beginning with BM should
therefore use srcOffset 54.

For types 2 and 3:

- There is no header, embedded dimension, row padding, or footer.
- Samples are little-endian uint16 values.
- Required raster extent is srcOffset + stride × height.
- Bytes beyond that extent are not consumed.
- Rows are consumed sequentially. Film calls ImportImg with orientation 0, so
  there is no vertical reversal. With a conventional positive-height BMP, the
  first raster row is conventionally the bottom row.

## Channel-slot semantics

The import workers do not swizzle channels:

- Type 0's 24-bit BMP worker, sub_10014410 at 0x10014410, copies conventional
  BMP bytes in their on-disk B, G, R order into slots 0, 1, and 2.
- Type 2's worker, sub_10017de0 at 0x10017de0, copies its three 16-bit slots
  unchanged and synthesizes slot 3 as 0xffff.
- Type 3's worker, sub_10019110 at 0x10019110, copies all four 16-bit slots
  unchanged.

Therefore, a synthetic 16-bit raw intended to match the conventional BMP path
should use B16, G16, R16, and optionally D16, all little-endian. For type 3,
D=0xffff is the safest neutral value because that is exactly what the type-2
importer supplies.

Engine diagnostics describe the conceptual planes as RGBD, but the scanner's
producer-side ordering was not independently recovered. The exact reader
contract is that slots are copied unchanged; BGR(D) is the interoperability
recommendation derived from the verified BMP path, not a claim about every
scanner firmware producer.

## Why the demo does not synthesize the film raster

The byte layout itself is recovered, but the complete film commands also
depend on correction/environment data such as CFName and the ICCS calibration
files. A conventional-file CmdID 19 conversion proves that the actual engine
can initialize, decode pixels, run its conversion worker, and encode a new
file without pretending that arbitrary RGB pixels are valid scanner-negative
measurements.

