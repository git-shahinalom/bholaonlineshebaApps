// Apps Script (forms/*.gs) এর যুক্তি Node-এ নকল Sheet/Drive দিয়ে পরীক্ষা।  ব্যবহার: node tests/gas_mock_test.js <jpeg-1000x600> <jpeg-300x200> <png-800x500>
const vm = require('vm'), fs = require('fs'), path = require('path');
const [, , bigJpg, tinyJpg, pngFile] = process.argv;
const signed = (p) => Array.from(fs.readFileSync(p)).map((b) => (b > 127 ? b - 256 : b));   // Apps Script বাইট = সাইনড

let failures = 0;
function check(name, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) failures++;
  console.log((ok ? 'OK   ' : 'FAIL ') + name + (ok ? '' : ` -> ${JSON.stringify(got)} (want ${JSON.stringify(want)})`));
}

function makeEnv(rowsByTab, fileBytes) {
  const log = { alerts: [], sharing: [] };
  class Range {
    constructor(s, r, c, nr, nc) { this.s = s; this.r = r; this.c = c; this.nr = nr; this.nc = nc; }
    getValues() {
      const out = [];
      for (let i = 0; i < this.nr; i++) { const row = []; for (let j = 0; j < this.nc; j++) { const v = (this.s.rows[this.r - 1 + i] || [])[this.c - 1 + j]; row.push(v === undefined ? '' : v); } out.push(row); }
      return out;
    }
    getValue() { return this.getValues()[0][0]; }
    setValue(v) { this.s.set(this.r, this.c, v); return this; }
    setValues(vs) { vs.forEach((row, i) => row.forEach((v, j) => this.s.set(this.r + i, this.c + j, v))); return this; }
    setDataValidation() { return this; } setFontWeight() { return this; }
    clearContents() { this.s.rows = []; return this; }
  }
  class Sheet {
    constructor(name, rows) { this.name = name; this.rows = rows; }
    set(r, c, v) { while (this.rows.length < r) this.rows.push([]); const row = this.rows[r - 1]; while (row.length < c) row.push(''); row[c - 1] = v; }
    getName() { return this.name; } getLastRow() { return this.rows.length; }
    getLastColumn() { return Math.max(0, ...this.rows.map((r) => r.length)); } getMaxRows() { return this.rows.length + 100; }
    getRange(r, c, nr = 1, nc = 1) { return new Range(this, r, c, nr, nc); }
    getFormUrl() { return ''; }
    clearContents() { this.rows = []; return this; }
  }
  const sheets = Object.entries(rowsByTab).map(([n, rows]) => new Sheet(n, rows.map((r) => r.slice())));
  const ss = { getSheets: () => sheets, getSheetByName: (n) => sheets.find((s) => s.name === n) || null,
    insertSheet(n) { const s = new Sheet(n, []); sheets.push(s); return s; }, getFormUrl: () => '' };
  const ctx = {
    console, JSON, Math, Date, String, Array, Object, parseFloat, isNaN, Error, RegExp, Number,
    SpreadsheetApp: { getActiveSpreadsheet: () => ss,
      getUi: () => ({ alert: (m) => log.alerts.push(m), createMenu: () => ({ addItem() { return this; }, addToUi() {} }), showModalDialog() {} }),
      newDataValidation: () => ({ requireValueInList() { return this; }, setAllowInvalid() { return this; }, build() { return {}; } }) },
    Utilities: { formatDate: () => '2026-10-22', base64Encode: (b) => Buffer.from(b.map((x) => x & 255)).toString('base64') },
    DriveApp: { Access: { ANYONE_WITH_LINK: 'ANYONE', PRIVATE: 'PRIVATE' }, Permission: { VIEW: 'VIEW', NONE: 'NONE' },
      getFileById: (id) => ({ setSharing: (a, p) => log.sharing.push([id, a]) }) },
    ScriptApp: { getOAuthToken: () => 'tok' },
    UrlFetchApp: { fetch: (url) => ({ getResponseCode: () => 200, getBlob: () => ({ getBytes: () => fileBytes(url), getContentType: () => 'image/jpeg' }) }) },
    HtmlService: { createHtmlOutput: () => ({ setWidth() { return this; }, setHeight() { return this; } }) },
  };
  ctx.Buffer = Buffer;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'forms', 'PhotoApprove.gs'), 'utf8'), ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'forms', 'SpotSetup.gs'), 'utf8'), ctx);
  return { ctx, ss, log };
}

const HDR = ['Timestamp', 'Email Address', 'স্থানের নাম', 'File upload', 'আপনার নাম', 'সম্মতি', 'অবস্থা', 'প্রকাশ-অবস্থা'];
const link = (id) => 'https://drive.google.com/open?id=' + id;
const BIG = signed(bigJpg), TINY = signed(tinyJpg), PNG = signed(pngFile);

// ---- ছবির মাপ (JPEG/PNG; সাইনড বাইট)
{
  const { ctx } = makeEnv({ X: [['a']] }, () => BIG);
  check('JPEG মাপ', ctx.photoImageSize_(BIG), [1000, 600]);
  check('ছোট JPEG মাপ', ctx.photoImageSize_(TINY), [300, 200]);
  check('PNG মাপ', ctx.photoImageSize_(PNG), [800, 500]);
  check('ছবি নয় → null', ctx.photoImageSize_([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]), null);
  check('ফাইল আইডি (open?id=)', ctx.photoFileId_('https://drive.google.com/open?id=ABCDEFGHIJKL12'), 'ABCDEFGHIJKL12');
  check('ফাইল আইডি (/file/d/)', ctx.photoFileId_('https://drive.google.com/file/d/ABCDEFGHIJKL12/view'), 'ABCDEFGHIJKL12');
  check('নাম পরিষ্কার', ctx.photoCleanName_('রহিম, উদ্দিন|\n x'), 'রহিম উদ্দিন x');
  check('ফাঁকা নাম', ctx.photoCleanName_(''), 'ব্যবহারকারী');
}

// ---- রিভিউ-উইন্ডো: পরের ছবি, এড়ানো, সিদ্ধান্ত
{
  const rows = [HDR,
    ['t', 'a@x.com', 'জ্যাকব টাওয়ার', link('IDAAAAAAAAAA1'), 'রহিম', 'ok', 'অপেক্ষমাণ', ''],
    ['t', 'b@x.com', 'তারুয়া সৈকত', link('IDBBBBBBBBBB2'), 'করিম', 'ok', '', ''],
    ['t', 'c@x.com', 'ঢালচর', link('IDCCCCCCCCCC3'), 'সালমা', 'ok', 'অনুমোদিত', ''],
    ['t', 'd@x.com', 'বেতুয়া', '', 'নাম', 'ok', 'অপেক্ষমাণ', '']];
  const { ctx, ss } = makeEnv({ 'Form Responses 1': rows }, (u) => (u.includes('IDBBBBBBBBBB2') ? TINY : BIG));
  let n = ctx.photoReviewNext([]);
  check('প্রথম অপেক্ষমাণ = সারি ২', [n.row, n.place, n.name, n.left], [2, 'জ্যাকব টাওয়ার', 'রহিম', 2]);
  check('মাপ ও "ছোট নয়"', [n.w, n.h, n.small], [1000, 600, false]);
  check('ছবি data-URI', n.dataUri.startsWith('data:image/jpeg;base64,'), true);
  n = ctx.photoReviewNext([2]);
  check('এড়ানোর পর = সারি ৩ (ফাঁকা অবস্থা = অপেক্ষমাণ)', n.row, 3);
  check('ছোট ছবি সতর্কতা', n.small, true);
  n = ctx.photoReviewNext([2, 3]);
  check('সব এড়ালে done', n.done, true);
  ctx.photoReviewDecide(2, 'অনুমোদিত');
  ctx.photoReviewDecide(3, 'বাতিল');
  const s = ss.getSheetByName('Form Responses 1');
  check('সিদ্ধান্ত শীটে লেখা', [s.rows[1][6], s.rows[2][6]], ['অনুমোদিত', 'বাতিল']);
  check('আর অপেক্ষমাণ ছবি নেই (আইডি-হীন সারি বাদ)', ctx.photoReviewNext([]).done, true);
  let threw = false; try { ctx.photoReviewDecide(2, 'যেকোনো'); } catch (e) { threw = true; }
  check('ভুল অবস্থা আটকায়', threw, true);
  threw = false; try { ctx.photoReviewDecide(99, 'অনুমোদিত'); } catch (e) { threw = true; }
  check('ভুল সারি আটকায়', threw, true);
}

// ---- প্রকাশের জন্য তৈরি
{
  const rows = [HDR.concat([])];
  const mk = (place, id, name, st) => ['t', 'secret@mail.com', place, id ? link(id) : '', name, 'ok', st, ''];
  rows.push(mk('জ্যাকব টাওয়ার', 'IDAAAAAAAAAA1', 'রহিম', 'অনুমোদিত'));
  rows.push(mk('জ্যাকব টাওয়ার', 'IDBBBBBBBBBB2', 'করিম, জুনিয়র', 'অনুমোদিত'));
  rows.push(mk('তারুয়া সৈকত', 'IDCCCCCCCCCC3', 'সালমা', 'বাতিল'));
  rows.push(mk('ঢালচর', 'IDDDDDDDDDDD4', 'নাসির', 'সরানো হোক'));
  rows.push(mk('বেতুয়া', '', 'আইডি নেই', 'অনুমোদিত'));
  rows.push(mk('খেজুরগাছিয়া', 'IDEEEEEEEEEE5', 'নতুন', 'অপেক্ষমাণ'));
  for (let i = 0; i < 6; i++) rows.push(mk('ইলিশা', 'IDXXXXXXXXXX' + i, 'ব্যবহারকারী' + i, 'অনুমোদিত'));   // ৬টিই, কিন্তু নিচে ৭ম
  rows.push(mk('ইলিশা', 'IDYYYYYYYYYY7', 'সপ্তম', 'অনুমোদিত'));
  const { ctx, ss, log } = makeEnv({ 'Form Responses 1': rows, 'প্রকাশিত': [] }, () => BIG);
  const c = ctx.photoPublishCore_();
  check('গণনা', c, { ok: 8, removed: 1, rejected: 1, pending: 1, err: 2 });
  const pub = ss.getSheetByName('প্রকাশিত').rows;
  check('প্রকাশিত ট্যাব হেডার', pub[0], ['স্থান', 'ফাইল আইডি', 'ছবির সূত্র', 'অনুমোদনের তারিখ']);
  check('প্রকাশিত সারি ৮টি + হেডার', pub.length, 9);
  check('নামে কমা মুছেছে', pub[2][2], 'করিম জুনিয়র');
  check('ইমেইল কোথাও যায়নি', JSON.stringify(pub).includes('secret@mail.com'), false);
  check('৭ম ছবি আটকেছে', pub.some((r) => r[1] === 'IDYYYYYYYYYY7'), false);
  const pubTab = ss.getSheetByName('Form Responses 1');
  check('৭ম ছবির প্রকাশ-অবস্থায় ❌', String(pubTab.rows[13][7]).startsWith('❌'), true);
  check('বাতিল/সরানো → ব্যক্তিগত', log.sharing.filter((x) => x[1] === 'PRIVATE').map((x) => x[0]).sort(), ['IDCCCCCCCCCC3', 'IDDDDDDDDDDD4']);
  check('অনুমোদিত → লিংকধারী সবাই', log.sharing.filter((x) => x[1] === 'ANYONE').length, 8);
  check('অপেক্ষমাণ ছবি প্রকাশ হয়নি', pub.some((r) => r[1] === 'IDEEEEEEEEEE5'), false);
  // তারিখ স্থির থাকে (আবার চালালে বদলায় না)
  pubTab.rows[1][7] = '✔ প্রকাশের জন্য তৈরি (2026-01-01)';
  ctx.photoPublishCore_();
  check('আগের অনুমোদনের তারিখ অক্ষত', ss.getSheetByName('প্রকাশিত').rows[1][3], '2026-01-01');
}

// ---- স্পট: স্থানাঙ্ক বের করা
{
  const { ctx } = makeEnv({ X: [['a']] }, () => BIG);
  const t = [['https://www.google.com/maps/place/Jacob/@22.1823,90.7511,17z/data=x', [22.1823, 90.7511]],
             ['22.6850, 90.6480', [22.685, 90.648]], ['https://www.google.com/maps?q=22.3,90.87', [22.3, 90.87]]];
  t.forEach(([s, w]) => check('স্থানাঙ্ক ' + s.slice(0, 40), ctx.spotCoordsIn_(s), w));
  check('ভোলার ভেতরে', [ctx.spotInBhola_(22.7, 90.6), ctx.spotInBhola_(40, 10)], [true, false]);
}

console.log(failures === 0 ? 'ALL PASS' : 'FAILS: ' + failures);
process.exit(failures === 0 ? 0 : 1);
