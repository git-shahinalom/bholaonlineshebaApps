/**
 * ভোলা অনলাইন সেবা: ইউজারের প্রস্তাবিত ভ্রমণ-স্পট (রুফটপ রেস্টুরেন্ট, পার্ক, লেক, রিসোর্ট…): ফর্ম বানানো ও অনুমোদন
 *
 * কোথায় বসাবে: একটি নতুন Google Sheet ("ভোলা স্পট - অনুমোদন" নাম দাও) → Extensions → Apps Script →
 *   এই পুরো লেখা পেস্ট → Save → Sheet রিফ্রেশ → উপরে "ভোলা স্পট" মেনু।
 *
 * মেনুর কাজ:
 *   ১) স্পট-ফর্ম বানাও: ফর্ম নিজে তৈরি হয় ও এই Sheet-এ উত্তর জমার ব্যবস্থা হয়। শেষে ফর্মের লিংক দেখায়।
 *   ২) অনুমোদনের কলাম সেটআপ: "অবস্থা" (অপেক্ষমাণ/অনুমোদিত/বাতিল/সরানো হোক), "প্রকাশ-অবস্থা", "অক্ষাংশ", "দ্রাঘিমাংশ"।
 *   ৩) অনুমোদিত স্পট প্রকাশের জন্য তৈরি করো: Google Maps লিংক থেকে স্থানাঙ্ক বের করে "স্পট-প্রকাশিত" ট্যাবে তোলে।
 *
 * কিছুই নিজে নিজে প্রকাশ হয় না: তুমি "অনুমোদিত" না বাছলে স্পট অ্যাপে যায় না।
 * ইমেইল ও "আপনি কে" শুধু এই Sheet-এ থাকে; "স্পট-প্রকাশিত" ট্যাবে কপি হয় না। শুধু ওই ট্যাব Publish to web করবে।
 * ফোন নম্বর তখনই প্রকাশিত ট্যাবে যায়, যদি ইউজার "নম্বর প্রকাশে সম্মতি" টিক দেন।
 */

var SPOT_Q = {
  type: 'স্পটের ধরন',
  name: 'স্পটের নাম',
  nameEn: 'নাম ইংরেজিতে (ঐচ্ছিক)',
  upazila: 'উপজেলা',
  area: 'এলাকা / ইউনিয়ন / ল্যান্ডমার্ক',
  map: 'Google Maps লিংক (অথবা অক্ষাংশ, দ্রাঘিমাংশ)',
  desc: 'এই স্থান কেন সুন্দর? সংক্ষেপে লিখুন',
  descEn: 'বিবরণ ইংরেজিতে (ঐচ্ছিক)',
  facilities: 'কী কী সুবিধা আছে?',
  hours: 'খোলা থাকার সময় / প্রবেশ ফি (জানা থাকলে)',
  phone: 'যোগাযোগের ফোন (ঐচ্ছিক)',
  phoneOk: 'ফোন নম্বর প্রকাশে সম্মতি',
  role: 'আপনি কে?',
  by: 'আপনার নাম (ঐচ্ছিক)',
  consent: 'সম্মতি'
};
var SPOT_C = {
  pubSheet: 'স্পট-প্রকাশিত',
  statusHeader: 'অবস্থা',
  pubHeader: 'প্রকাশ-অবস্থা',
  latHeader: 'অক্ষাংশ',
  lngHeader: 'দ্রাঘিমাংশ',
  states: ['অপেক্ষমাণ', 'অনুমোদিত', 'বাতিল', 'সরানো হোক'],
  upazilas: ['ভোলা সদর', 'বোরহানউদ্দিন', 'চরফ্যাশন', 'দৌলতখান', 'লালমোহন', 'মনপুরা', 'তজুমদ্দিন'],
  types: ['রেস্টুরেন্ট (রুফটপ / ক্যাফে)', 'পার্ক', 'জলাশয় (নদীতীর / লেক / দিঘি)', 'প্রকৃতি (চর / দ্বীপ / বন)',
          'রিসোর্ট', 'সৈকত', 'দর্শনীয় (ঐতিহাসিক / বিখ্যাত স্থাপনা)', 'অন্যান্য'],
  facilities: ['পার্কিং', 'পরিবার-বান্ধব', 'খাবার পাওয়া যায়', 'নৌবিহার', 'ছবি তোলার সুন্দর জায়গা',
               'রাতে খোলা', 'প্রবেশ টিকিট লাগে', 'শিশুদের জন্য ভালো', 'বসার ব্যবস্থা'],
  consent: ['তথ্য আমার জানামতে সঠিক',
            'স্থানটি সবার জন্য উন্মুক্ত (বা অনুমতি নিয়ে ঢোকা যায়); ব্যক্তিগত বা নিষিদ্ধ এলাকা নয়',
            'ডেভেলপার যাচাই করে প্রকাশ করবেন; ভালো না হলে প্রকাশ নাও হতে পারে এবং পরে সরানো হতে পারে',
            'মূল্য, মান বা নিরাপত্তার দায় অ্যাপ নেয় না, আমি তা জানি'],
  minLat: 21.5, maxLat: 23.2, minLng: 90.0, maxLng: 91.5,
  maxPerUpazila: 40
};

function spotMenu_() {
  SpreadsheetApp.getUi().createMenu('ভোলা স্পট')
    .addItem('১) স্পট-ফর্ম বানাও', 'spotCreateForm')
    .addItem('২) অনুমোদনের কলাম সেটআপ', 'spotSetup')
    .addItem('৩) অনুমোদিত স্পট প্রকাশের জন্য তৈরি করো', 'spotPublish')
    .addToUi();
}

// ---------------------------------------------------------------- ফর্ম

function spotCreateForm() {
  var ui = SpreadsheetApp.getUi();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (ss.getFormUrl()) {
    ui.alert('এই Sheet-এ ফর্ম আগে থেকেই যুক্ত আছে:\n' + FormApp.openByUrl(ss.getFormUrl()).getPublishedUrl() +
      '\n\nনতুন ফর্ম লাগলে নতুন Sheet খুলে সেখানে চালাও।');
    return;
  }
  var form = FormApp.create('ভোলার নতুন ভ্রমণ-স্পট প্রস্তাব');
  form.setDescription('আপনার জানা সুন্দর কোনো রুফটপ রেস্টুরেন্ট, পার্ক, লেক, প্রাকৃতিক রিসোর্ট বা দর্শনীয় স্থান ভোলা অনলাইন সেবা অ্যাপে যুক্ত করার প্রস্তাব দিন।\n' +
    'ডেভেলপার যাচাই করে অনুমোদন দিলেই কেবল স্পটটি অ্যাপে দেখা যাবে। আপনার ইমেইল কখনো প্রকাশ হবে না।');
  form.setCollectEmail(true);
  form.setConfirmationMessage('ধন্যবাদ! আপনার প্রস্তাব পেয়েছি। যাচাই করে অনুমোদন দিলে স্পটটি অ্যাপে দেখা যাবে।');
  form.setShowLinkToRespondAgain(true);

  form.addMultipleChoiceItem().setTitle(SPOT_Q.type).setChoiceValues(SPOT_C.types).setRequired(true);
  form.addTextItem().setTitle(SPOT_Q.name).setRequired(true);
  form.addTextItem().setTitle(SPOT_Q.nameEn).setHelpText('ইংরেজি অ্যাপ-ব্যবহারকারীদের জন্য');
  form.addListItem().setTitle(SPOT_Q.upazila).setChoiceValues(SPOT_C.upazilas).setRequired(true);
  form.addTextItem().setTitle(SPOT_Q.area).setHelpText('যেমন: লঞ্চঘাট রোড, ইলিশা, কেন্দ্রীয় মসজিদের পাশে');
  form.addTextItem().setTitle(SPOT_Q.map).setRequired(true)
    .setHelpText('Google Maps-এ স্থানটি খুলে Share → Copy link দিয়ে লিংকটি পেস্ট করুন। অথবা মানচিত্রে স্থানটি চেপে ধরলে উপরে যে সংখ্যা (যেমন 22.6850, 90.6480) দেখায়, সেটি লিখুন।');
  form.addParagraphTextItem().setTitle(SPOT_Q.desc).setRequired(true)
    .setHelpText('২-৩ বাক্যে। কী দেখা যায়, কেন ভালো লাগে। (৩০০ অক্ষরের মধ্যে; লিংক বা বিজ্ঞাপন দেবেন না)')
    .setValidation(FormApp.createParagraphTextValidation().requireTextLengthLessThanOrEqualTo(300).build());
  form.addParagraphTextItem().setTitle(SPOT_Q.descEn).setHelpText('ঐচ্ছিক')
    .setValidation(FormApp.createParagraphTextValidation().requireTextLengthLessThanOrEqualTo(300).build());
  form.addCheckboxItem().setTitle(SPOT_Q.facilities).setChoiceValues(SPOT_C.facilities);
  form.addTextItem().setTitle(SPOT_Q.hours).setHelpText('যেমন: বিকাল ৪টা–রাত ১০টা; প্রবেশ ফি নেই');
  form.addTextItem().setTitle(SPOT_Q.phone).setHelpText('প্রতিষ্ঠানের নম্বর হলে। ব্যক্তিগত নম্বর দেবেন না।');
  form.addCheckboxItem().setTitle(SPOT_Q.phoneOk).setChoiceValues(['এই নম্বর অ্যাপে প্রকাশ করা যাবে']);
  form.addMultipleChoiceItem().setTitle(SPOT_Q.role).setChoiceValues(['মালিক / ব্যবস্থাপক', 'স্থানীয় বাসিন্দা', 'পর্যটক / ঘুরতে গিয়েছিলাম'])
    .setRequired(true).setHelpText('শুধু যাচাইয়ের জন্য; প্রকাশ হবে না');
  form.addTextItem().setTitle(SPOT_Q.by).setHelpText('দিলে অ্যাপে "প্রস্তাবক: নাম" দেখানো হতে পারে (ইমেইল নয়)');
  form.addCheckboxItem().setTitle(SPOT_Q.consent).setChoiceValues(SPOT_C.consent).setRequired(true)
    .setValidation(FormApp.createCheckboxValidation().requireSelectAtLeast(SPOT_C.consent.length)
      .setHelpText('সবকটিতে টিক দিতে হবে').build());

  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  ui.alert('ফর্ম তৈরি ✔\n\nউত্তর দেওয়ার লিংক (অ্যাপের spot_form_url এ বসাও):\n' + form.getPublishedUrl() +
    '\n\nসম্পাদনার লিংক:\n' + form.getEditUrl() +
    '\n\nএবার মেনু থেকে "২) অনুমোদনের কলাম সেটআপ" চালাও। (Sheet-এ উত্তর-ট্যাব তৈরি হতে ১০ সেকেন্ড লাগতে পারে; রিফ্রেশ করো।)');
}

// ---------------------------------------------------------------- অনুমোদন

function spotResponseSheet_() {
  var sheets = SpreadsheetApp.getActiveSpreadsheet().getSheets();
  for (var i = 0; i < sheets.length; i++) {
    if (sheets[i].getName() === SPOT_C.pubSheet || !sheets[i].getLastColumn()) continue;
    var h = sheets[i].getRange(1, 1, 1, sheets[i].getLastColumn()).getValues()[0];
    if (h.indexOf(SPOT_Q.name) >= 0 && h.indexOf(SPOT_Q.map) >= 0) return sheets[i];
  }
  throw new Error('উত্তর-ট্যাব পাওয়া যায়নি। আগে "১) স্পট-ফর্ম বানাও" চালাও এবং Sheet রিফ্রেশ করো।');
}

function spotHeaders_(sheet) {
  return sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
}

function spotEnsureColumn_(sheet, title) {
  var h = spotHeaders_(sheet);
  var i = h.indexOf(title);
  if (i >= 0) return i + 1;
  var col = sheet.getLastColumn() + 1;
  sheet.getRange(1, col).setValue(title).setFontWeight('bold');
  return col;
}

function spotSetup() {
  var sheet = spotResponseSheet_();
  var statusCol = spotEnsureColumn_(sheet, SPOT_C.statusHeader);
  spotEnsureColumn_(sheet, SPOT_C.pubHeader);
  spotEnsureColumn_(sheet, SPOT_C.latHeader);
  spotEnsureColumn_(sheet, SPOT_C.lngHeader);
  var rows = Math.max(sheet.getMaxRows() - 1, 1);
  sheet.getRange(2, statusCol, rows, 1).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(SPOT_C.states, true).setAllowInvalid(false).build());
  var last = sheet.getLastRow();
  if (last >= 2) {
    var rng = sheet.getRange(2, statusCol, last - 1, 1);
    var v = rng.getValues();
    for (var i = 0; i < v.length; i++) if (!v[i][0]) v[i][0] = 'অপেক্ষমাণ';
    rng.setValues(v);
  }
  var pub = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SPOT_C.pubSheet) ||
            SpreadsheetApp.getActiveSpreadsheet().insertSheet(SPOT_C.pubSheet);
  pub.getRange(1, 1, 1, 14).setValues([spotPubHeader_()]).setFontWeight('bold');
  SpreadsheetApp.getUi().alert('সেটআপ শেষ ✔\n\nনতুন প্রস্তাব এলে প্রতিটি পড়ে "অবস্থা" ঘরে বাছো:\n• অনুমোদিত = অ্যাপে দেখাবে\n• বাতিল = দেখাবে না\n• সরানো হোক = আগে অনুমোদিত ছিল, এখন সরাতে চাই\n\n' +
    'চাইলে বিবরণ বা নামের বানান Sheet-এই ঠিক করে নিতে পারো; যা এখানে থাকবে, তাই অ্যাপে যাবে।\nতারপর মেনু ৩) চালাও।');
}

function spotPubHeader_() {
  return ['ধরন', 'নাম', 'নাম (ইংরেজি)', 'উপজেলা', 'এলাকা', 'অক্ষাংশ', 'দ্রাঘিমাংশ', 'বিবরণ', 'বিবরণ (ইংরেজি)',
          'সুবিধা', 'সময়/ফি', 'ফোন', 'প্রস্তাবক', 'অনুমোদনের তারিখ'];
}

function spotToday_() {
  return Utilities.formatDate(new Date(), 'Asia/Dhaka', 'yyyy-MM-dd');
}

function spotClean_(v, max) {
  var s = String(v == null ? '' : v).replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim();
  return s.substring(0, max);
}

/** লেখা বা Google Maps লিংক থেকে [অক্ষাংশ, দ্রাঘিমাংশ]; না পেলে null। ছোট লিংক (maps.app.goo.gl) অনুসরণ করে। */
function spotParseCoords_(text) {
  var s = String(text || '').trim();
  var c = spotCoordsIn_(s);
  if (c) return c;
  var m = s.match(/https?:\/\/\S+/);
  if (!m) return null;
  var url = m[0];
  for (var i = 0; i < 6; i++) {
    c = spotCoordsIn_(decodeURIComponent(url));
    if (c) return c;
    var res;
    try {
      res = UrlFetchApp.fetch(url, { followRedirects: false, muteHttpExceptions: true });
    } catch (e) {
      return null;
    }
    var code = res.getResponseCode();
    var loc = res.getHeaders()['Location'] || res.getHeaders()['location'];
    if (code >= 300 && code < 400 && loc) {
      url = loc;
      continue;
    }
    if (code === 200) return spotCoordsIn_(res.getContentText().substring(0, 200000));
    return null;
  }
  return null;
}

function spotCoordsIn_(s) {
  var m = s.match(/@(-?\d{1,2}\.\d+),(-?\d{2,3}\.\d+)/) ||
          s.match(/!3d(-?\d{1,2}\.\d+)!4d(-?\d{2,3}\.\d+)/) ||
          s.match(/[?&](?:q|ll|query|center)=(-?\d{1,2}\.\d+)(?:,|%2C)\s*(-?\d{2,3}\.\d+)/) ||
          s.match(/^\s*(-?\d{1,2}\.\d{3,})\s*[,\s]\s*(-?\d{2,3}\.\d{3,})\s*$/);
  return m ? [parseFloat(m[1]), parseFloat(m[2])] : null;
}

function spotInBhola_(lat, lng) {
  return lat >= SPOT_C.minLat && lat <= SPOT_C.maxLat && lng >= SPOT_C.minLng && lng <= SPOT_C.maxLng;
}

function spotPublish() {
  var ui = SpreadsheetApp.getUi();
  var sheet = spotResponseSheet_();
  var h = spotHeaders_(sheet);
  var idx = function (t) { return h.indexOf(t); };
  var cStatus = idx(SPOT_C.statusHeader), cPub = idx(SPOT_C.pubHeader), cLat = idx(SPOT_C.latHeader), cLng = idx(SPOT_C.lngHeader);
  if (cStatus < 0 || cPub < 0 || cLat < 0 || cLng < 0) { ui.alert('আগে "২) অনুমোদনের কলাম সেটআপ" চালাও।'); return; }
  var pub = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SPOT_C.pubSheet);
  if (!pub) { ui.alert('"' + SPOT_C.pubSheet + '" ট্যাব নেই। আগে সেটআপ চালাও।'); return; }
  var last = sheet.getLastRow();
  if (last < 2) { ui.alert('এখনো কোনো প্রস্তাব নেই।'); return; }

  var data = sheet.getRange(2, 1, last - 1, sheet.getLastColumn()).getValues();
  var out = [spotPubHeader_()];
  var seen = {}, perUp = {};
  var n = { ok: 0, removed: 0, rejected: 0, pending: 0, err: 0 };

  for (var i = 0; i < data.length; i++) {
    var row = data[i];
    var r = i + 2;
    var status = String(row[cStatus] || 'অপেক্ষমাণ').trim();
    var pubCell = sheet.getRange(r, cPub + 1);
    if (status === 'সরানো হোক') { pubCell.setValue('🗑 সরানো হয়েছে'); n.removed++; continue; }
    if (status === 'বাতিল') { pubCell.setValue('✖ বাতিল'); n.rejected++; continue; }
    if (status !== 'অনুমোদিত') { pubCell.setValue(''); n.pending++; continue; }

    var name = spotClean_(row[idx(SPOT_Q.name)], 80);
    var up = spotClean_(row[idx(SPOT_Q.upazila)], 20);
    var typeLabel = String(row[idx(SPOT_Q.type)] || '');
    var type = typeLabel.split(' (')[0].trim() || 'অন্যান্য';
    if (!name || SPOT_C.upazilas.indexOf(up) < 0) { pubCell.setValue('❌ নাম বা উপজেলা ঠিক নয়'); n.err++; continue; }
    var key = up + '|' + name;
    if (seen[key]) { pubCell.setValue('❌ একই স্পট আগেও অনুমোদিত'); n.err++; continue; }
    perUp[up] = (perUp[up] || 0) + 1;
    if (perUp[up] > SPOT_C.maxPerUpazila) { pubCell.setValue('❌ এই উপজেলায় ' + SPOT_C.maxPerUpazila + 'টি স্পট হয়ে গেছে'); n.err++; continue; }

    // স্থানাঙ্ক: হাতে বসানো থাকলে সেটাই; নাহলে লিংক থেকে বের করে ঘরে লিখে রাখি (ভুল হলে তুমি ঠিক করতে পারো)
    var lat = parseFloat(row[cLat]), lng = parseFloat(row[cLng]);
    if (isNaN(lat) || isNaN(lng)) {
      var c = spotParseCoords_(row[idx(SPOT_Q.map)]);
      if (c) { lat = c[0]; lng = c[1]; sheet.getRange(r, cLat + 1).setValue(lat); sheet.getRange(r, cLng + 1).setValue(lng); }
    }
    if (isNaN(lat) || isNaN(lng) || !spotInBhola_(lat, lng)) {
      pubCell.setValue('❌ স্থানাঙ্ক পাওয়া যায়নি বা ভোলার বাইরে। মানচিত্র লিংক খুলে সংখ্যা অক্ষাংশ/দ্রাঘিমাংশ ঘরে লেখো');
      n.err++; continue;
    }
    seen[key] = true;

    var prev = String(pubCell.getValue() || '');
    var m = prev.match(/(\d{4}-\d{2}-\d{2})/);
    var date = m ? m[1] : spotToday_();
    var phone = String(row[idx(SPOT_Q.phoneOk)] || '').length ? spotClean_(row[idx(SPOT_Q.phone)], 20) : '';
    out.push([type, name, spotClean_(row[idx(SPOT_Q.nameEn)], 80), up, spotClean_(row[idx(SPOT_Q.area)], 60), lat, lng,
              spotClean_(row[idx(SPOT_Q.desc)], 300), spotClean_(row[idx(SPOT_Q.descEn)], 300),
              spotClean_(row[idx(SPOT_Q.facilities)], 120).replace(/,\s*/g, '، '), spotClean_(row[idx(SPOT_Q.hours)], 80),
              phone, spotClean_(row[idx(SPOT_Q.by)], 40), date]);
    pubCell.setValue('✔ প্রকাশের জন্য তৈরি (' + date + ')');
    n.ok++;
  }

  pub.clearContents();
  pub.getRange(1, 1, out.length, 14).setValues(out);
  pub.getRange(1, 1, 1, 14).setFontWeight('bold');
  ui.alert('হয়েছে ✔\n\nঅনুমোদিত: ' + n.ok + ' · সরানো: ' + n.removed + ' · বাতিল: ' + n.rejected + ' · অপেক্ষমাণ: ' + n.pending +
    (n.err ? ' · সমস্যা: ' + n.err + ' ("প্রকাশ-অবস্থা" কলাম দেখো)' : '') +
    '\n\nএখন GitHub → Actions → "Sync approved photos and spots" → Run workflow চাপলে অ্যাপে আসবে (না চাপলে ৬ ঘণ্টার মধ্যে নিজেই আসবে)।');
}
