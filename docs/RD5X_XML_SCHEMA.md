# Noritsu RD5X ICCS XML command schema

This describes the request parser in ImageDataProc\ImgCorrectDLL.dll and the
parts exercised against the Windows 10 VM. Addresses are image virtual
addresses in ImgCorrectDLL.dll unless stated otherwise.

## Document rules

- File entry: 0x101f0b40; BSTR entry: 0x101f0d10.
- Root dispatch: 0x101efb80; request parser: 0x101ee480.
- The engine serializer uses the root name ICCS. The parser obtains the
  document element but does not compare its name; use ICCS for compatibility.
- Names are case-sensitive. Values are element text, not attributes.
- Root children and compound children are selected by name, so sibling order
  is immaterial. Unknown elements are ignored.
- A scalar is effectively optional and single-valued: the first matching child
  is read. Repeated values and records are siblings with the same name; they
  need not be consecutive, and there is no array wrapper.
- The syntactic parser permits absent leaves. Semantic validation decides what
  a command requires.
- Command files should be UTF-16LE with a BOM. The serializer declares
  version="1.0" encoding="UTF-16".

Type notation below:

- i32: signed 32-bit integer
- u8/u16/u32: unsigned integer of that width
- f64: double-precision number
- string260/string256: bounded internal wide-character fields
- T[N]: at most N repeated sibling elements of type T

## Root request tree

~~~text
ICCS
├── CmdHD
├── MdlPrm
├── TrzParam
├── FramPara
└── ImgFileInfReq
~~~

All five root children are syntactically 0..1.

### CmdHD — 0x101ed3a0

~~~text
CmdHD
├── ModuleID                    string
├── EnvDir                     string256
├── CmdID                      i32
├── Info                       string260
├── DstCacheEnable             i32
├── DstCacheEnable2            i32
├── NumCpuParallel             i32
├── FileIoMode                 u8
├── JpgToBmpConvEngine         u8
├── AvgDiskQueueLengthLimit    f64
└── AvgDiskQueueLengthWaitTime u32
~~~

Semantic validation at 0x101ca250 requires ModuleID to be present and exactly
NKC-ICCS, and CmdID to be present and recognized. If a nonempty EnvDir is
provided, the engine validates its ICCS.CNO and ICCS.HKX environment files.

### MdlPrm — 0x101ee290

~~~text
MdlPrm
├── EnvDir string256
├── GNo    u16
├── MNo    u16
├── SNo    u16
└── Key    string
~~~

### TrzParam — 0x101ed520

~~~text
TrzParam
├── PieceNum i32
└── TrzCorInf string260
~~~

### ImgFileInfReq — 0x101ee3a0

~~~text
ImgFileInfReq
├── FileName              string260
├── NkcDCRawOutFileName   string260
└── AdobeDNGConvDir       string260
~~~

CmdID 17 consumes ImgFileInfReq/FileName.

### FramPara — 0x101ed5f0

~~~text
FramPara
├── CFName      string260
├── CorInf
├── CorType
├── FrameInf
├── CmsInf
├── NxNInf
├── MediaInf
├── ImgInf
├── ImgFltInf
├── ToneCrv
├── SpotRev
├── SoftRev
├── CrsRev
├── REyeRev
├── MrgRev
├── AbrRev
├── DstRev
├── TpzRev
├── AutoCrs
└── AlpChInf
~~~

The correction-family commands 2 through 12, 104, and 106 require CFName.
CmdID 19 accepts FramPara/ImgInf with just SrcImg and DstImg.

#### CorInf — 0x101e72c0

All leaves are i32:

~~~text
FixColSw FaceFind AtRedEye MLimPos PLimPos MLimRto PLimRto MRto PRto
StdDnsSw StdColSw ScnDnsSw ScnColSw REyeRto TngLev CF
~~~

#### CorType — 0x101e7480

All leaves are i32: CorType, ColCorInt, ConCorInt.

#### FrameInf — 0x101ec910

~~~text
PMCFName string260
AcVal AcSVal AcHVal AsVal SatVal GrainVal MoireVal DodVal i32
PntMode RedEyeSW SftFilSW CrsFilSW SptFilSW MrgSW i32
AbrSW DstSW TpzSW AlgoType SgsSW AsMode CcdHVal JpgHLV i32
TotalBal i32[3]
ScnSlp[4]
  ├── Cor      f64
  ├── Bal      i32[3]
  ├── Sat      i32
  └── Con      i32
SlopeRVal i32
SlopeBVal i32
~~~

Each ScnSlp is a directly repeated ScnSlp child containing its record fields.

#### CmsInf — 0x101eccf0

~~~text
CmsSW     i32
CmsDatFlg i32
CmsDat    string260
~~~

#### NxNInf — 0x101e7650

All leaves are i32: EgSW, DspEgInt, EgMskSiz.

#### MediaInf — 0x101e7730

All leaves are i32: MedKind, MedType, PriKind.

#### ImgInf — 0x101ecdd0

~~~text
SrcImg       string260
OptMag       f64
DigMagV      f64
DigMagH      f64
ScnCrg       i32
SrcOfst      i32
SrcCh        i32
SrcBpc       i32
SrcColOdr    i32
SrcWid       i32
SrcHei       i32
SrcColSp     i32
RalRct       i32[4]
DstImg       string260
DstOfst      i32
DstCh        i32
DstBpc       i32
DstColOdr    i32
DstBtmUpFlg  i32
Qlt          i32
DstWid       i32
DstHei       i32
VerMirFlg    i32
HorMirFlg    i32
~~~

Example repeated-array encoding:

~~~xml
<RalRct>0</RalRct>
<RalRct>0</RalRct>
<RalRct>640</RalRct>
<RalRct>480</RalRct>
~~~

#### ImgFltInf — 0x101e7810

~~~text
TrmRct1 i32[4]
ZmWid   i32
ZmHei   i32
Deg     f64
TrmRct2 i32[4]
TrmRct3 i32[4]
BlkCol  i32[3]
~~~

#### ToneCrv — 0x101e7940

~~~text
GamNumR GamNumG GamNumB GamNumD i32
PDatR PgamR PDatG PgamG PDatB PgamB PDatD PgamD f64[20] each
~~~

#### SpotRev — 0x101e7bf0

~~~text
Extent   i32
SpotInfN i32
SpotInf[100]
  ├── CentX CentY Rad f64
  └── Flag ID ADFlg  i32
~~~

SpotInf record parser: 0x101e7ae0.

#### SoftRev — 0x101e7f00

~~~text
FilType  i32
Int      i32
SoftInfN i32
SoftInf[10]
  ├── CentX CentY Rad f64
  ├── RotAgl          i32
  ├── VHRat           f64
  └── ID ADFlg        i32
~~~

SoftInf record parser: 0x101e7de0.

#### CrsRev — 0x101e8210

~~~text
Ptn Num Agl Wid CrsInfN i32
CrsInf[100]
  ├── CentX CentY f64
  ├── Lng         i32
  ├── Dat         f64
  └── ID ADFlg    i32
~~~

CrsInf record parser: 0x101e8100.

#### REyeRev — 0x101ed1b0

~~~text
REyeInfN i32
REyeInf[50]
  ├── AreaType                    i32
  ├── CentX CentY Rad             f64
  ├── CorMeth ID ADFlg CorFlg     i32
  ├── REyeCutSrcImg               string260
  └── REyeCutDstImg               string260
~~~

REyeInf record parser: 0x101ed050.

#### MrgRev — 0x101e8430

CenSftX and CenSftY are f64. RotAgl, Int, and VHRatio are i32.

#### AbrRev — 0x101e8530

CenSftX and CenSftY are f64. Vdef and Hdef are each i32[3].

#### DstRev — 0x101e8620

CenSftX and CenSftY are f64. ElpsX and ElpsY are i32.

#### TpzRev — 0x101e8710

CenSftX and CenSftY are f64. SlpX and SlpY are i32.

#### AutoCrs — 0x101e8800

All leaves are i32: Min, Permit, Length, MaxNum.

#### AlpChInf — 0x101e88f0

All leaves are i32: ElgType, TrnType, EgVol, EgSiz.

## Command IDs

The dispatch table is at 0x10299908.

| CmdID | Handler |
| ---: | --- |
| 0 | GetImageCorrectModule |
| 1 | PreparaDispForMedia |
| 2 | CalcAutoCorrection |
| 3 | PreparaDispForFilm |
| 4 | CreateDispForMedia |
| 5 | CreateDispForFilm |
| 6 | CreateOutputForMedia |
| 7 | CreateOutputForFilm |
| 8 | GetAutoRedEyeParam |
| 9 | GetRedEyeFindParam |
| 10 | GetCrossFindParam |
| 11 | GetFaceFindParam |
| 12 | GetCorrectionParam |
| 13 | ProcessResizeImage |
| 14 | ProcessCMS |
| 15 | ProcessSharpness |
| 16 | ProcessChangeFormat |
| 17 | GetImgFileInf |
| 18 | ProcessDoRotation |
| 19 | ProcessDoFormatConv |
| 101 | PreparaDispForDRaw |
| 104 | CreateDispForDRaw |
| 106 | CreateOutputForDRaw |

## Minimal verified commands

CmdID 19 converts an ordinary file and writes DstImg:

~~~xml
<?xml version="1.0" encoding="utf-16"?>
<ICCS>
  <CmdHD>
    <ModuleID>NKC-ICCS</ModuleID>
    <CmdID>19</CmdID>
  </CmdHD>
  <FramPara>
    <ImgInf>
      <SrcImg><engine-dir>\headless-input.bmp</SrcImg>
      <DstImg><engine-dir>\headless-output.bmp</DstImg>
    </ImgInf>
  </FramPara>
</ICCS>
~~~

CmdID 17 reports ordinary-file metadata:

~~~xml
<?xml version="1.0" encoding="utf-16"?>
<ICCS>
  <CmdHD>
    <ModuleID>NKC-ICCS</ModuleID>
    <CmdID>17</CmdID>
  </CmdHD>
  <ImgFileInfReq>
    <FileName><engine-dir>\headless-input.bmp</FileName>
  </ImgFileInfReq>
</ICCS>
~~~

Call CmdID 17 with an Ex method. Its command-specific response is:

~~~xml
<?xml version="1.0" encoding="UTF-16"?>
<ICCS>
  <ImgFileInf>
    <FileName xml:space="preserve"><engine-dir>\headless-input.bmp</FileName>
    <ImgFmt xml:space="preserve">BMP</ImgFmt>
    <cc>0</cc>
    <bpc>0</bpc>
    <bpp>32</bpp>
    <co>0</co>
    <Width>64</Width>
    <Height>48</Height>
  </ImgFileInf>
</ICCS>
~~~

The serializer may omit response fields whose presence flags are false.

## Similar strings that are not request fields

- ImgFileInf is CmdID 17 output.
- ImgType, MaxImgSizeOnMem, NegaTypeNo, PosiTypeNo, MediaTypeNo,
  DRawTypeNo, IQGTypeNo, and the Type/TypeInf families are module-description
  response or configuration data.
- ColGam, CmsAlgType, and CorrOpt are environment-option XML, not accepted by
  the request parser.
- FilType is specifically FramPara/SoftRev/FilType.
- GamNumR/G/B/D and PgamR/G/B/D are specifically under FramPara/ToneCrv.
- NkcDCRawOutFileName is under the root ImgFileInfReq.
