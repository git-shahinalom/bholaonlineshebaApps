/**
 * ভোলা অনলাইন সেবা: ছবি দেখা ও অনুমোদন
 *
 * কোথায় বসাবে: ছবির ফর্মের উত্তর যে Google Sheet-এ জমে (যেমন "ভোলা সেবা - যাচাই")
 *   Extensions → Apps Script → এই ফাইল (PhotoApprove.gs) + Menu.gs যোগ করো → Save → Sheet রিফ্রেশ।
 *   (একই প্রজেক্টে FormSetup.gs / SpotSetup.gs থাকলেও চলবে; নামের সংঘর্ষ নেই।)
 *
 * মেনু "ভোলা ছবি":
 *   ১) প্রথমবার সেটআপ
 *   ২) ছবি দেখে অনুমোদন করো: প্রতিটি অপেক্ষমাণ ছবি উইন্ডোতে দেখাবে (মাপসহ); [অনুমোদন] [বাতিল] [এড়িয়ে যাও]
 *   ৩) অনুমোদিত ছবি প্রকাশের জন্য তৈরি করো
 *   ৪) ফর্মের স্থানের তালিকা হালনাগাদ করো
 *
 * গোপনীয়তা: "প্রকাশিত" ট্যাবে শুধু স্থান, ফাইল আইডি, নাম ও তারিখ যায়; ইমেইল কখনো না। শুধু ওই ট্যাব Publish to web করবে।
 */

// অ্যাপের ডেটা-ফাইল (GitHub Pages)। তোমার সাইটের ঠিকানা না মিললে এখানে ঠিক করো।
var PHOTO_DATA_JSON_URL = 'https://git-shahinalom.github.io/bholaonlineshebaApps/data.json';

var PHOTO_CFG = {
  pubSheet: 'প্রকাশিত',
  statusHeader: 'অবস্থা',
  pubHeader: 'প্রকাশ-অবস্থা',
  states: ['অপেক্ষমাণ', 'অনুমোদিত', 'বাতিল', 'সরানো হোক'],
  maxPerPlace: 6,
  minW: 700,
  minH: 400,
  // হেডার চেনার নিয়ম। ফর্মের প্রশ্নের নাম বদলালে এখানে মেলাও।
  placeRe: /স্থান/,
  photoRe: /ছবি|file upload/i,
  nameRe: /আপনার নাম|^নাম$|your name/i
};

function photoMenu_() {
  SpreadsheetApp.getUi().createMenu('ভোলা ছবি')
    .addItem('১) প্রথমবার সেটআপ', 'photoSetup')
    .addItem('২) ছবি দেখে অনুমোদন করো', 'photoReview')
    .addItem('৩) অনুমোদিত ছবি প্রকাশের জন্য তৈরি করো', 'photoPublish')
    .addItem('৪) ফর্মের স্থানের তালিকা হালনাগাদ করো', 'photoRefreshPlaces')
    .addToUi();
}

// ---------------------------------------------------------------- শীট ও কলাম

/** উত্তর-ট্যাব: যেটার হেডারে ছবির কলাম আছে ("প্রকাশিত" ট্যাব বাদে)। */
function photoResponseSheet_() {
  var sheets = SpreadsheetApp.getActiveSpreadsheet().getSheets();
  for (var i = 0; i < sheets.length; i++) {
    if (sheets[i].getName() === PHOTO_CFG.pubSheet) continue;
    var lastCol = sheets[i].getLastColumn();
    if (!lastCol) continue;
    var h = sheets[i].getRange(1, 1, 1, lastCol).getValues()[0];
    for (var c = 0; c < h.length; c++) {
      if (PHOTO_CFG.photoRe.test(String(h[c]))) return sheets[i];
    }
  }
  throw new Error('ছবির কলামসহ উত্তর-ট্যাব পাওয়া যায়নি। ফর্মের Responses → Link to Sheets করা হয়েছে তো?');
}

function photoColIndex_(headers, re, label) {
  for (var c = 0; c < headers.length; c++) {
    if (re.test(String(headers[c])) && !(label === 'name' && /স্থান/.test(String(headers[c])))) return c;
  }
  return -1;
}

function photoHeaderRow_(sheet) {
  return sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
}

function photoEnsureColumn_(sheet, title) {
  var h = photoHeaderRow_(sheet);
  for (var c = 0; c < h.length; c++) if (String(h[c]) === title) return c + 1;
  var col = sheet.getLastColumn() + 1;
  sheet.getRange(1, col).setValue(title).setFontWeight('bold');
  return col;
}

function photoSetup() {
  var ui = SpreadsheetApp.getUi();
  var sheet = photoResponseSheet_();
  var statusCol = photoEnsureColumn_(sheet, PHOTO_CFG.statusHeader);
  var pubCol = photoEnsureColumn_(sheet, PHOTO_CFG.pubHeader);
  var rows = Math.max(sheet.getMaxRows() - 1, 1);
  var rule = SpreadsheetApp.newDataValidation().requireValueInList(PHOTO_CFG.states, true).setAllowInvalid(false).build();
  sheet.getRange(2, statusCol, rows, 1).setDataValidation(rule);
  var last = sheet.getLastRow();
  if (last >= 2) {
    var rng = sheet.getRange(2, statusCol, last - 1, 1);
    var v = rng.getValues();
    for (var i = 0; i < v.length; i++) if (!v[i][0]) v[i][0] = 'অপেক্ষমাণ';
    rng.setValues(v);
  }
  var pub = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(PHOTO_CFG.pubSheet);
  if (!pub) pub = SpreadsheetApp.getActiveSpreadsheet().insertSheet(PHOTO_CFG.pubSheet);
  pub.getRange(1, 1, 1, 4).setValues([['স্থান', 'ফাইল আইডি', 'ছবির সূত্র', 'অনুমোদনের তারিখ']]).setFontWeight('bold');
  ui.alert('সেটআপ শেষ ✔\n\nএখন মেনু "২) ছবি দেখে অনুমোদন করো" চালাও: প্রতিটি ছবি দেখে অনুমোদন বা বাতিল করবে।\n(হাতে করতে চাইলে "অবস্থা" ঘরে বাছো: অনুমোদিত / বাতিল / সরানো হোক।)\n\nশেষে মেনু ৩) চালাও।');
}

// ---------------------------------------------------------------- সাহায্যকারী

/** ফর্মের ফাইল-আপলোড ঘরের লেখা (…/open?id=ID বা …/file/d/ID/…) থেকে ফাইল আইডি। */
function photoFileId_(cell) {
  var s = String(cell || '');
  var m = s.match(/[?&]id=([A-Za-z0-9_-]{10,})/) || s.match(/\/d\/([A-Za-z0-9_-]{10,})/);
  return m ? m[1] : '';
}

function photoCleanName_(v) {
  var s = String(v || '').replace(/[,|\n\r\t]+/g, ' ').replace(/\s+/g, ' ').trim();
  return (s || 'ব্যবহারকারী').substring(0, 40);
}

function photoToday_() {
  return Utilities.formatDate(new Date(), 'Asia/Dhaka', 'yyyy-MM-dd');
}

/** ছবির বাইট থেকে [প্রস্থ, উচ্চতা] (JPEG বা PNG); না বুঝলে null। বাইটগুলো Apps Script-এর (-128..127) হতে পারে। */
function photoImageSize_(bytes) {
  var b = function (i) { return bytes[i] & 0xFF; };
  if (bytes.length > 24 && b(0) === 0x89 && b(1) === 0x50 && b(2) === 0x4E && b(3) === 0x47) {
    return [(b(16) << 24 | b(17) << 16 | b(18) << 8 | b(19)) >>> 0, (b(20) << 24 | b(21) << 16 | b(22) << 8 | b(23)) >>> 0];
  }
  if (bytes.length > 4 && b(0) === 0xFF && b(1) === 0xD8) {
    var i = 2;
    while (i + 9 < bytes.length) {
      if (b(i) !== 0xFF) { i++; continue; }
      var marker = b(i + 1);
      if (marker === 0xFF) { i++; continue; }
      if (marker >= 0xC0 && marker <= 0xCF && marker !== 0xC4 && marker !== 0xC8 && marker !== 0xCC) {
        return [(b(i + 7) << 8) | b(i + 8), (b(i + 5) << 8) | b(i + 6)];
      }
      if (marker === 0xD8 || marker === 0x01 || (marker >= 0xD0 && marker <= 0xD7)) { i += 2; continue; }
      i += 2 + ((b(i + 2) << 8) | b(i + 3));
    }
  }
  return null;
}

// ---------------------------------------------------------------- ছবি দেখে অনুমোদন (উইন্ডো)

function photoReview() {
  var ui = SpreadsheetApp.getUi();
  var sheet = photoResponseSheet_();
  var h = photoHeaderRow_(sheet);
  if (h.indexOf(PHOTO_CFG.statusHeader) < 0) { ui.alert('আগে মেনু "১) প্রথমবার সেটআপ" চালাও।'); return; }
  var html = HtmlService.createHtmlOutput(PHOTO_REVIEW_HTML_).setWidth(560).setHeight(640);
  ui.showModalDialog(html, 'ছবি দেখে অনুমোদন');
}

/** উইন্ডো থেকে ডাকা হয়: পরের অপেক্ষমাণ ছবি (skip = এড়িয়ে যাওয়া সারির তালিকা)। না থাকলে null। */
function photoReviewNext(skip) {
  var sheet = photoResponseSheet_();
  var h = photoHeaderRow_(sheet);
  var cPlace = photoColIndex_(h, PHOTO_CFG.placeRe, 'place');
  var cPhoto = photoColIndex_(h, PHOTO_CFG.photoRe, 'photo');
  var cName = photoColIndex_(h, PHOTO_CFG.nameRe, 'name');
  var cStatus = h.indexOf(PHOTO_CFG.statusHeader);
  var last = sheet.getLastRow();
  if (last < 2) return null;
  var data = sheet.getRange(2, 1, last - 1, sheet.getLastColumn()).getValues();
  skip = skip || [];
  var pending = [];
  for (var i = 0; i < data.length; i++) {
    var st = String(data[i][cStatus] || 'অপেক্ষমাণ').trim();
    if (st !== 'অপেক্ষমাণ') continue;
    if (!photoFileId_(data[i][cPhoto])) continue;
    pending.push(i + 2);
  }
  var left = pending.length;
  var row = null;
  for (var k = 0; k < pending.length; k++) if (skip.indexOf(pending[k]) < 0) { row = pending[k]; break; }
  if (row === null) return { done: true, left: left };

  var r = data[row - 2];
  var id = photoFileId_(r[cPhoto]);
  var out = { done: false, row: row, left: left, place: String(r[cPlace] || ''), name: cName >= 0 ? String(r[cName] || '') : '',
              id: id, link: 'https://drive.google.com/file/d/' + id + '/view' };
  try {
    var resp = UrlFetchApp.fetch('https://drive.google.com/thumbnail?id=' + id + '&sz=w1200',
      { headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() }, muteHttpExceptions: true });
    if (resp.getResponseCode() === 200) {
      var blob = resp.getBlob();
      var bytes = blob.getBytes();
      var size = photoImageSize_(bytes);
      out.dataUri = 'data:' + (blob.getContentType() || 'image/jpeg') + ';base64,' + Utilities.base64Encode(bytes);
      if (size) { out.w = size[0]; out.h = size[1]; out.small = size[0] < PHOTO_CFG.minW || size[1] < PHOTO_CFG.minH; }
    } else {
      out.error = 'ছবি আনা যায়নি (HTTP ' + resp.getResponseCode() + ')। নিচের "নতুন ট্যাবে খোলো" চাপো।';
    }
  } catch (e) {
    out.error = 'ছবি আনা যায়নি: ' + e.message;
  }
  return out;
}

function photoReviewDecide(row, status) {
  if (['অনুমোদিত', 'বাতিল'].indexOf(status) < 0) throw new Error('ভুল অবস্থা');
  var sheet = photoResponseSheet_();
  var h = photoHeaderRow_(sheet);
  var cStatus = h.indexOf(PHOTO_CFG.statusHeader);
  if (cStatus < 0 || row < 2 || row > sheet.getLastRow()) throw new Error('সারি ঠিক নয়');
  sheet.getRange(row, cStatus + 1).setValue(status);
  return true;
}

/** উইন্ডোর শেষ বোতাম: প্রকাশের জন্য তৈরি (বার্তা-বাক্স ছাড়া)। */
function photoPublishFromDialog() {
  var n = photoPublishCore_();
  return n;
}

var PHOTO_REVIEW_HTML_ = '' +
  '<style>body{font-family:Arial,sans-serif;margin:0;padding:14px;color:#222}' +
  '#img{max-width:100%;max-height:340px;display:block;margin:8px auto;border-radius:8px;background:#eee}' +
  '.row{display:flex;gap:8px;margin-top:12px}button{flex:1;padding:12px;font-size:15px;border:0;border-radius:8px;cursor:pointer}' +
  '#ok{background:#2e8b77;color:#fff}#no{background:#c62828;color:#fff}#skip{background:#ddd}' +
  '.warn{background:#fff3cd;color:#6d4c00;padding:8px;border-radius:6px;margin-top:8px}.meta{margin-top:6px;line-height:1.5}' +
  'a{color:#1a73e8}</style><div id="box">লোড হচ্ছে…</div>' +
  '<script>var skip=[];' +
  'function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"}[c]})}' +
  'function load(){document.getElementById("box").innerHTML="লোড হচ্ছে…";' +
  'google.script.run.withSuccessHandler(show).withFailureHandler(err).photoReviewNext(skip)}' +
  'function show(d){var b=document.getElementById("box");' +
  'if(!d||d.done){b.innerHTML="<h3>🎉 আর কোনো অপেক্ষমাণ ছবি নেই</h3><p>এখন প্রকাশের জন্য তৈরি করবে?</p>' +
  '<div class=row><button id=ok onclick=pub()>প্রকাশের জন্য তৈরি করো</button><button id=skip onclick=google.script.host.close()>বন্ধ করো</button></div>";return}' +
  'var h="<div class=meta><b>"+esc(d.place)+"</b> · "+esc(d.name||"নাম নেই")+" · বাকি "+d.left+"টি</div>";' +
  'if(d.dataUri){h+="<img id=img src=\\""+d.dataUri+"\\">"}' +
  'if(d.w){h+="<div class=meta>মাপ: "+d.w+"×"+d.h+" px</div>"}' +
  'if(d.small){h+="<div class=warn>⚠ ছবি ছোট (৭০০×৪০০ এর কম); অ্যাপে খারাপ দেখাবে। বাতিল করা ভালো।</div>"}' +
  'if(d.error){h+="<div class=warn>"+esc(d.error)+"</div>"}' +
  'h+="<div class=meta><a href=\\""+d.link+"\\" target=_blank>নতুন ট্যাবে বড় করে খোলো</a></div>";' +
  'h+="<div class=row><button id=ok onclick=\\"decide("+d.row+",\'অনুমোদিত\')\\">✔ অনুমোদন</button>' +
  '<button id=no onclick=\\"decide("+d.row+",\'বাতিল\')\\">✖ বাতিল</button>' +
  '<button id=skip onclick=\\"skip.push("+d.row+");load()\\">এড়িয়ে যাও</button></div>";b.innerHTML=h}' +
  'function decide(row,st){var bs=document.getElementsByTagName("button");for(var i=0;i<bs.length;i++)bs[i].disabled=true;' +
  'google.script.run.withSuccessHandler(load).withFailureHandler(err).photoReviewDecide(row,st)}' +
  'function pub(){document.getElementById("box").innerHTML="তৈরি হচ্ছে…";' +
  'google.script.run.withSuccessHandler(function(n){document.getElementById("box").innerHTML="<h3>✔ হয়েছে</h3><p>অনুমোদিত: "+n.ok+" · সরানো: "+n.removed+" · বাতিল: "+n.rejected+(n.err?" · সমস্যা: "+n.err:"")+"</p><p>এখন GitHub → Actions → <b>Sync approved photos and spots</b> → Run workflow।</p><div class=row><button id=skip onclick=google.script.host.close()>বন্ধ করো</button></div>"}).withFailureHandler(err).photoPublishFromDialog()}' +
  'function err(e){document.getElementById("box").innerHTML="<div class=warn>সমস্যা: "+esc(e.message||e)+"</div>"}' +
  'load()</script>';

// ---------------------------------------------------------------- প্রকাশের জন্য তৈরি

function photoPublish() {
  var ui = SpreadsheetApp.getUi();
  var n;
  try {
    n = photoPublishCore_();
  } catch (e) {
    ui.alert(e.message);
    return;
  }
  ui.alert('হয়েছে ✔\n\nঅনুমোদিত: ' + n.ok + ' · সরানো: ' + n.removed + ' · বাতিল: ' + n.rejected +
    ' · অপেক্ষমাণ: ' + n.pending + (n.err ? ' · সমস্যা: ' + n.err + ' (প্রকাশ-অবস্থা কলাম দেখো)' : '') +
    '\n\nএখন GitHub → Actions → "Sync approved photos and spots" → Run workflow চাপলে ছবি অ্যাপে আসবে (না চাপলে ৬ ঘণ্টার মধ্যে নিজেই আসবে)।');
}

/** অনুমোদিত সারি "প্রকাশিত" ট্যাবে তোলে; সংখ্যা ফেরত দেয়। সমস্যা হলে ব্যতিক্রম ছোঁড়ে। */
function photoPublishCore_() {
  var sheet = photoResponseSheet_();
  var h = photoHeaderRow_(sheet);
  var cPlace = photoColIndex_(h, PHOTO_CFG.placeRe, 'place');
  var cPhoto = photoColIndex_(h, PHOTO_CFG.photoRe, 'photo');
  var cName = photoColIndex_(h, PHOTO_CFG.nameRe, 'name');
  var cStatus = h.indexOf(PHOTO_CFG.statusHeader);
  var cPub = h.indexOf(PHOTO_CFG.pubHeader);
  if (cPlace < 0 || cPhoto < 0 || cStatus < 0 || cPub < 0) {
    throw new Error('আগে মেনু থেকে "১) প্রথমবার সেটআপ" চালাও।');
  }
  var pub = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(PHOTO_CFG.pubSheet);
  if (!pub) throw new Error('"' + PHOTO_CFG.pubSheet + '" ট্যাব নেই। আগে সেটআপ চালাও।');
  var last = sheet.getLastRow();
  var counts = { ok: 0, removed: 0, rejected: 0, pending: 0, err: 0 };
  if (last < 2) return counts;

  var data = sheet.getRange(2, 1, last - 1, sheet.getLastColumn()).getValues();
  var out = [['স্থান', 'ফাইল আইডি', 'ছবির সূত্র', 'অনুমোদনের তারিখ']];
  var perPlace = {};

  for (var i = 0; i < data.length; i++) {
    var row = data[i];
    var status = String(row[cStatus] || 'অপেক্ষমাণ').trim();
    var id = photoFileId_(row[cPhoto]);
    var pubCell = sheet.getRange(i + 2, cPub + 1);
    var place = String(row[cPlace] || '').trim();

    if (status === 'অনুমোদিত') {
      if (!id || !place) { pubCell.setValue('❌ ছবি বা স্থানের নাম নেই'); counts.err++; continue; }
      perPlace[place] = (perPlace[place] || 0) + 1;
      if (perPlace[place] > PHOTO_CFG.maxPerPlace) {
        pubCell.setValue('❌ এই স্থানে ' + PHOTO_CFG.maxPerPlace + 'টি ছবি হয়ে গেছে; আগে একটা সরাও');
        counts.err++; continue;
      }
      try {
        DriveApp.getFileById(id).setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
      } catch (e) {
        pubCell.setValue('❌ ফাইল খোলা যায়নি: ' + e.message); counts.err++; continue;
      }
      var prev = String(pubCell.getValue() || '');
      var m = prev.match(/(\d{4}-\d{2}-\d{2})/);
      var date = m ? m[1] : photoToday_();
      out.push([place, id, photoCleanName_(cName >= 0 ? row[cName] : ''), date]);
      pubCell.setValue('✔ প্রকাশের জন্য তৈরি (' + date + ')');
      counts.ok++;
    } else if (status === 'সরানো হোক' || status === 'বাতিল') {
      if (id) { try { DriveApp.getFileById(id).setSharing(DriveApp.Access.PRIVATE, DriveApp.Permission.NONE); } catch (e) {} }
      pubCell.setValue(status === 'বাতিল' ? '✖ বাতিল' : '🗑 সরানো হয়েছে');
      if (status === 'বাতিল') counts.rejected++; else counts.removed++;
    } else {
      pubCell.setValue('');
      counts.pending++;
    }
  }

  pub.clearContents();
  pub.getRange(1, 1, out.length, 4).setValues(out);
  pub.getRange(1, 1, 1, 4).setFontWeight('bold');
  return counts;
}

// ---------------------------------------------------------------- ফর্মের স্থানের তালিকা

/**
 * ফর্মের "স্থানের নাম" ড্রপডাউন অ্যাপের বর্তমান তালিকা (নতুন অনুমোদিত স্পটসহ) দিয়ে ভরে দেয়,
 * যাতে ইউজার নতুন স্পটেও ছবি পাঠাতে পারে।
 */
function photoRefreshPlaces() {
  var ui = SpreadsheetApp.getUi();
  var formUrl = '';
  try {
    formUrl = photoResponseSheet_().getFormUrl() || SpreadsheetApp.getActiveSpreadsheet().getFormUrl() || '';
  } catch (e) {
    formUrl = SpreadsheetApp.getActiveSpreadsheet().getFormUrl() || '';
  }
  if (!formUrl) { ui.alert('ছবির উত্তর-ট্যাবে ফর্ম যুক্ত নেই (ফর্মের Responses → Link to Sheets করা হয়েছে তো?)।'); return; }
  var res = UrlFetchApp.fetch(PHOTO_DATA_JSON_URL + '?t=' + new Date().getTime(), { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) { ui.alert('ডেটা আনা যায়নি (HTTP ' + res.getResponseCode() + '). PHOTO_DATA_JSON_URL ঠিক আছে তো?'); return; }
  var all = JSON.parse(res.getContentText()).data;
  var names = [];
  Object.keys(all).forEach(function (up) {
    (all[up].tourism || []).forEach(function (it) {
      if (!it.demo && names.indexOf(it.name) < 0) names.push(it.name);
    });
  });
  names.sort();
  if (!names.length) { ui.alert('কোনো ভ্রমণের স্থান পাওয়া যায়নি।'); return; }
  var form = FormApp.openByUrl(formUrl);
  var items = form.getItems(FormApp.ItemType.LIST);
  var target = null;
  for (var i = 0; i < items.length; i++) if (PHOTO_CFG.placeRe.test(items[i].getTitle())) target = items[i].asListItem();
  if (!target) { ui.alert('"স্থানের নাম" নামে ড্রপডাউন প্রশ্ন পাওয়া যায়নি (ফর্মে প্রশ্নটি Dropdown ধরনের হতে হবে)।'); return; }
  target.setChoiceValues(names);
  ui.alert('ফর্মের তালিকা হালনাগাদ ✔ (' + names.length + 'টি স্থান)');
}
