/**
 * ভোলা অনলাইন সেবা: প্রতিষ্ঠানের তথ্য জমা ফর্ম + যাচাই ব্যবস্থা
 *
 * ব্যবহার:
 *  ১. নতুন Google Sheet খোলো (নাম: "ভোলা সেবা - যাচাই")
 *  ২. Extensions → Apps Script → এই পুরো কোড পেস্ট → Save → শীট রিফ্রেশ করো
 *  ৩. উপরের মেনু "ভোলা সেবা" থেকে ধাপগুলো ক্রমে চালাও (প্রথমবার অনুমতি চাইবে)
 */

// ---------------------------------------------------------------- সেটিংস

var UPAZILA_CHOICES = ['ভোলা সদর', 'বোরহানউদ্দিন', 'চরফ্যাশন', 'দৌলতখান', 'লালমোহন', 'মনপুরা', 'তজুমদ্দিন'];

// ফর্মের "সেবার ধরন" → data.csv এর ক্যাটাগরি
var CATEGORY_MAP = {
  'হাসপাতাল / ক্লিনিক / ডায়াগনস্টিক সেন্টার': 'হাসপাতাল',
  'এ্যাম্বুলেন্স সেবা': 'এ্যাম্বুলেন্স',
  'রেন্ট-এ-কার / যানবাহন': 'রেন্ট-এ-কার',
  'আইনি সহায়তা / আইনজীবী': 'আইনজীবী',
  'বিদ্যুৎ অফিস / অভিযোগ কেন্দ্র': 'জরুরি বিদ্যুৎ'
};

var REQ_NEW = 'নতুন তথ্য যুক্ত করতে চাই';
var REQ_EDIT = 'তথ্য সংশোধন করতে চাই';
var REQ_REMOVE = 'তালিকা থেকে সরাতে চাই';

// প্রশ্নের শিরোনাম: এই শিরোনাম ধরেই উত্তর খোঁজা হয়, তাই ফর্মে শিরোনাম বদলালে এখানেও বদলাতে হবে
var Q = {
  request: 'অনুরোধের ধরন',
  category: 'সেবার ধরন',
  upazila: 'উপজেলা',
  name: 'প্রতিষ্ঠান বা সেবার নাম',
  address: 'পূর্ণ ঠিকানা',
  phone: 'ফোন নম্বর (অ্যাপে কল বাটনে দেখাবে)',
  phone2: 'বিকল্প ফোন নম্বর (ঐচ্ছিক)',
  hours: 'সেবার সময় (ঐচ্ছিক)',
  link: 'ফেসবুক পেজ বা ওয়েবসাইটের লিংক',
  applicant: 'আবেদনকারীর নাম ও পদবি (প্রকাশ হবে না)',
  email: 'ইমেইল (ঐচ্ছিক, প্রকাশ হবে না)',
  consent: 'সম্মতি',

  h_type: 'হাসপাতাল: প্রতিষ্ঠানের ধরন',
  h_er: 'হাসপাতাল: জরুরি বিভাগ ২৪ ঘণ্টা খোলা?',
  h_services: 'হাসপাতাল: যেসব সেবা আছে',
  h_license: 'হাসপাতাল: স্বাস্থ্য অধিদপ্তরের নিবন্ধন নম্বর (প্রকাশ হবে না)',

  a_owner: 'এ্যাম্বুলেন্স: কারা পরিচালনা করেন?',
  a_type: 'এ্যাম্বুলেন্স: গাড়ির ধরন',
  a_24h: 'এ্যাম্বুলেন্স: ২৪ ঘণ্টা সেবা?',
  a_area: 'এ্যাম্বুলেন্স: কোন এলাকায় সেবা দেন?',

  r_types: 'যানবাহন: কী কী ভাড়া দেন?',
  r_driver: 'যানবাহন: চালকসহ ভাড়া?',
  r_area: 'যানবাহন: কোন এলাকায় সেবা দেন?',
  r_license: 'যানবাহন: ট্রেড লাইসেন্স বা নিবন্ধন নম্বর (প্রকাশ হবে না)',

  l_kind: 'আইনি সেবা: আবেদনকারীর ধরন',
  l_fields: 'আইনি সেবা: কোন ক্ষেত্রে সেবা দেন?',
  l_license: 'আইনি সেবা: বার কাউন্সিল বা সনদ নম্বর (প্রকাশ হবে না)',

  e_kind: 'বিদ্যুৎ: অফিসের ধরন',
  e_services: 'বিদ্যুৎ: কী কী সেবা?',
  e_24h: 'বিদ্যুৎ: ২৪ ঘণ্টা অভিযোগ গ্রহণ?'
};

// রিভিউ কলাম (ফর্মের উত্তরের ডানদিকে যোগ হয়)
var REV = {
  status: 'স্ট্যাটাস',
  date: 'যাচাইয়ের তারিখ',
  note: 'যাচাইকারীর নোট',
  exported: 'CSV এ নেওয়া হয়েছে'
};
var ST_PENDING = 'অপেক্ষমাণ';
var ST_APPROVED = 'অনুমোদিত';
var ST_REJECTED = 'বাতিল';

var CSV_HEADER = ['উপজেলা', 'ক্যাটাগরি', 'নাম', 'ঠিকানা', 'ফোন', 'নোট', 'দেখাবে?', 'নমুনা?', 'যাচাই তারিখ'];

// ---------------------------------------------------------------- মেনু

function onOpen() {
  SpreadsheetApp.getUi().createMenu('ভোলা সেবা')
    .addItem('১. ফর্ম তৈরি করো (প্রথমবার)', 'createForm')
    .addItem('২. রিভিউ কলাম ঠিক করো', 'setupReview')
    .addItem('৩. অনুমোদিত সারি CSV এ নাও', 'exportApproved')
    .addSeparator()
    .addItem('ফর্মের লিংক দেখাও', 'showLinks')
    .addItem('নতুন জমা এলে ইমেইলে জানাও (চালু)', 'installNotify')
    .addToUi();
}

function ui_(msg) {
  try { SpreadsheetApp.getUi().alert(msg); } catch (e) { Logger.log(msg); }
}

// ---------------------------------------------------------------- ফর্ম তৈরি

function createForm() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var props = PropertiesService.getDocumentProperties();
  if (props.getProperty('formId')) {
    ui_('ফর্ম আগেই তৈরি হয়েছে। লিংক দেখতে মেনু থেকে "ফর্মের লিংক দেখাও" চাপো।');
    return;
  }

  var form = FormApp.create('ভোলা অনলাইন সেবা - প্রতিষ্ঠানের তথ্য জমা দিন');
  form.setDescription(
    'ভোলা অনলাইন সেবা অ্যাপে আপনার হাসপাতাল, এ্যাম্বুলেন্স, যানবাহন, আইনি সহায়তা বা বিদ্যুৎ অফিসের তথ্য যুক্ত করতে এই ফর্ম পূরণ করুন।\n\n' +
    '• জমা দেওয়ার পর ডেভেলপার আপনার দেওয়া নম্বরে ফোন করে তথ্য যাচাই করবেন।\n' +
    '• যাচাই শেষ হলে তথ্য অ্যাপে প্রকাশিত হবে। জমা দিলেই প্রকাশের নিশ্চয়তা নেই।\n' +
    '• ভুল, বিভ্রান্তিকর বা অন্যের তথ্য দিলে আবেদন বাতিল হবে।\n' +
    '• নম্বর ও সংখ্যা ইংরেজি অঙ্কে লিখুন (যেমন 01712345678)।');
  form.setConfirmationMessage('ধন্যবাদ! আপনার তথ্য জমা হয়েছে। যাচাইয়ের জন্য ডেভেলপার আপনার নম্বরে যোগাযোগ করবেন।');
  form.setAllowResponseEdits(false);
  form.setShowLinkToRespondAgain(true);
  form.setProgressBar(true);

  // ---- পাতা ১: সাধারণ তথ্য
  form.addMultipleChoiceItem().setTitle(Q.request).setChoiceValues([REQ_NEW, REQ_EDIT, REQ_REMOVE]).setRequired(true);
  var catItem = form.addMultipleChoiceItem().setTitle(Q.category).setRequired(true);
  form.addListItem().setTitle(Q.upazila).setChoiceValues(UPAZILA_CHOICES).setRequired(true);
  form.addTextItem().setTitle(Q.name).setRequired(true);
  form.addParagraphTextItem().setTitle(Q.address).setHelpText('গ্রাম/রোড, ইউনিয়ন বা পৌরসভা, নিকটবর্তী পরিচিত স্থান').setRequired(true);

  // ---- হাসপাতাল
  var pH = form.addPageBreakItem().setTitle('হাসপাতাল / ক্লিনিক / ডায়াগনস্টিক সেন্টারের তথ্য');
  form.addMultipleChoiceItem().setTitle(Q.h_type).setChoiceValues([
    'সরকারি হাসপাতাল', 'বেসরকারি হাসপাতাল', 'ক্লিনিক', 'ডায়াগনস্টিক সেন্টার', 'ডায়ালাইসিস সেন্টার', 'ব্লাড ব্যাংক', 'অন্য']).setRequired(true);
  form.addMultipleChoiceItem().setTitle(Q.h_er).setChoiceValues(['হ্যাঁ', 'না']).setRequired(true);
  form.addCheckboxItem().setTitle(Q.h_services).setChoiceValues([
    'ইমার্জেন্সি', 'আইসিইউ', 'ডায়ালাইসিস', 'অপারেশন থিয়েটার', 'প্যাথলজি / ল্যাব', 'এক্স-রে', 'আল্ট্রাসনোগ্রাফি', 'ইসিজি', 'ব্লাড ব্যাংক', 'এ্যাম্বুলেন্স', 'ফার্মেসি']);
  form.addTextItem().setTitle(Q.h_license).setHelpText('বেসরকারি প্রতিষ্ঠানের জন্য। এটি অ্যাপে প্রকাশ হবে না, শুধু যাচাইয়ে লাগবে। সরকারি প্রতিষ্ঠান হলে "সরকারি" লিখুন।');

  // ---- এ্যাম্বুলেন্স
  var pA = form.addPageBreakItem().setTitle('এ্যাম্বুলেন্স সেবার তথ্য');
  form.addMultipleChoiceItem().setTitle(Q.a_owner).setChoiceValues([
    'হাসপাতাল / ক্লিনিক', 'সংস্থা বা সংগঠন', 'ব্যক্তিগত মালিক', 'সরকারি / ফায়ার সার্ভিস']).setRequired(true);
  form.addCheckboxItem().setTitle(Q.a_type).setChoiceValues([
    'সাধারণ', 'এসি', 'আইসিইউ / লাইফ সাপোর্ট', 'ফ্রিজিং (লাশবাহী)', 'নৌ-এ্যাম্বুলেন্স']).setRequired(true);
  form.addMultipleChoiceItem().setTitle(Q.a_24h).setChoiceValues(['হ্যাঁ', 'না']).setRequired(true);
  form.addTextItem().setTitle(Q.a_area);

  // ---- যানবাহন
  var pR = form.addPageBreakItem().setTitle('রেন্ট-এ-কার / যানবাহন সেবার তথ্য');
  form.addCheckboxItem().setTitle(Q.r_types).setChoiceValues([
    'প্রাইভেট কার', 'মাইক্রোবাস', 'পিকআপ / ট্রাক', 'বাস', 'মোটরসাইকেল', 'অটো / সিএনজি', 'স্পিডবোট / ট্রলার', 'অন্য']).setRequired(true);
  form.addMultipleChoiceItem().setTitle(Q.r_driver).setChoiceValues(['চালকসহ', 'শুধু গাড়ি', 'দুটোই']).setRequired(true);
  form.addTextItem().setTitle(Q.r_area);
  form.addTextItem().setTitle(Q.r_license).setHelpText('প্রকাশ হবে না, শুধু যাচাইয়ে লাগবে।');

  // ---- আইনি সহায়তা
  var pL = form.addPageBreakItem().setTitle('আইনি সহায়তা / আইনজীবীর তথ্য');
  form.addMultipleChoiceItem().setTitle(Q.l_kind).setChoiceValues([
    'আইনজীবী (ব্যক্তি)', 'আইনজীবী সমিতি / বার অ্যাসোসিয়েশন', 'আইনি সহায়তা কেন্দ্র / এনজিও', 'সরকারি লিগ্যাল এইড অফিস']).setRequired(true);
  form.addCheckboxItem().setTitle(Q.l_fields).setChoiceValues([
    'দেওয়ানি', 'ফৌজদারি', 'পারিবারিক', 'ভূমি', 'নারী ও শিশু অধিকার', 'শ্রম', 'সাইবার']);
  form.addTextItem().setTitle(Q.l_license).setHelpText('আইনজীবীর ক্ষেত্রে প্রযোজ্য। প্রকাশ হবে না, শুধু যাচাইয়ে লাগবে।');

  // ---- বিদ্যুৎ
  var pE = form.addPageBreakItem().setTitle('বিদ্যুৎ অফিস / অভিযোগ কেন্দ্রের তথ্য');
  form.addMultipleChoiceItem().setTitle(Q.e_kind).setChoiceValues([
    'পল্লী বিদ্যুৎ সমিতি', 'বিউবো (BPDB)', 'অভিযোগ কেন্দ্র / জোনাল অফিস', 'অন্য']).setRequired(true);
  form.addCheckboxItem().setTitle(Q.e_services).setChoiceValues([
    'বিদ্যুৎ নেই / লাইন কাটা অভিযোগ', 'নতুন সংযোগ', 'বিল সংক্রান্ত', 'মিটার সমস্যা']);
  form.addMultipleChoiceItem().setTitle(Q.e_24h).setChoiceValues(['হ্যাঁ', 'না']);

  // ---- সাধারণ শেষ পাতা
  var pC = form.addPageBreakItem().setTitle('যোগাযোগ ও সম্মতি')
    .setHelpText('নিচের নম্বরটি অ্যাপে "কল করুন" বাটনে দেখানো হবে। অন্য তথ্য শুধু যাচাইয়ের জন্য।');
  var phoneRule = FormApp.createTextValidation()
    .setHelpText('ইংরেজি অঙ্কে লিখুন, যেমন 01712345678')
    .requireTextMatchesPattern('^[0-9+\\-\\s]{5,20}$').build();
  form.addTextItem().setTitle(Q.phone).setValidation(phoneRule).setRequired(true);
  form.addTextItem().setTitle(Q.phone2).setValidation(phoneRule);
  form.addTextItem().setTitle(Q.hours).setHelpText('যেমন: ২৪ ঘণ্টা / সকাল ৯টা থেকে রাত ৯টা');
  form.addTextItem().setTitle(Q.link).setHelpText('যাচাইয়ে সহায়তা করে। না থাকলে ফাঁকা রাখুন।');
  form.addTextItem().setTitle(Q.applicant).setRequired(true);
  form.addTextItem().setTitle(Q.email).setValidation(FormApp.createTextValidation().requireTextIsEmail().build());
  form.addCheckboxItem().setTitle(Q.consent).setChoiceValues([
    'আমি এই প্রতিষ্ঠান/সেবার অনুমোদিত প্রতিনিধি। দেওয়া তথ্য সত্য। নাম, ঠিকানা ও ফোন নম্বর অ্যাপে সবার জন্য প্রকাশ হবে, এবং যাচাইয়ের জন্য ডেভেলপার আমার সাথে যোগাযোগ করতে পারেন।'
  ]).setRequired(true);

  // ---- শাখা: সেবার ধরন অনুযায়ী পাতায় যাওয়া, তারপর সবাই শেষ পাতায়
  [pH, pA, pR, pL, pE].forEach(function (p) { p.setGoToPage(pC); });
  catItem.setChoices([
    catItem.createChoice('হাসপাতাল / ক্লিনিক / ডায়াগনস্টিক সেন্টার', pH),
    catItem.createChoice('এ্যাম্বুলেন্স সেবা', pA),
    catItem.createChoice('রেন্ট-এ-কার / যানবাহন', pR),
    catItem.createChoice('আইনি সহায়তা / আইনজীবী', pL),
    catItem.createChoice('বিদ্যুৎ অফিস / অভিযোগ কেন্দ্র', pE)
  ]);

  // ---- উত্তর এই শীটেই আসবে
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  props.setProperty('formId', form.getId());
  props.setProperty('sheetUrl', ss.getUrl());
  SpreadsheetApp.flush();

  var ok = setupReview_();
  var short = '';
  try { short = form.shortenFormUrl(form.getPublishedUrl()); } catch (e) { short = form.getPublishedUrl(); }
  props.setProperty('formUrl', short);
  ui_('✅ ফর্ম তৈরি হয়েছে।\n\nজনসাধারণের লিংক (এটা অ্যাপে বসাবে):\n' + short +
      '\n\nসম্পাদনার লিংক (শুধু তোমার):\n' + form.getEditUrl() +
      (ok ? '' : '\n\nরিভিউ কলাম পরে মেনু থেকে "২. রিভিউ কলাম ঠিক করো" চালিয়ে বসাও।'));
}

function showLinks() {
  var props = PropertiesService.getDocumentProperties();
  var id = props.getProperty('formId');
  if (!id) { ui_('এখনো ফর্ম তৈরি হয়নি।'); return; }
  var form = FormApp.openById(id);
  ui_('জনসাধারণের লিংক:\n' + (props.getProperty('formUrl') || form.getPublishedUrl()) +
      '\n\nসম্পাদনার লিংক:\n' + form.getEditUrl());
}

// ---------------------------------------------------------------- রিভিউ কলাম

function findResponsesSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var formId = PropertiesService.getDocumentProperties().getProperty('formId');
  if (!formId) return null;
  var sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    var url = sheets[i].getFormUrl();
    if (!url) continue;
    try { if (FormApp.openByUrl(url).getId() === formId) return sheets[i]; } catch (e) { /* পরেরটা দেখি */ }
  }
  return null;
}

function setupReview() {
  ui_(setupReview_() ? '✅ রিভিউ কলাম ঠিক আছে (স্ট্যাটাস, যাচাইয়ের তারিখ, নোট)।' :
      'উত্তরের শীট পাওয়া যায়নি। আগে "১. ফর্ম তৈরি করো" চালাও, বা একটা পরীক্ষামূলক উত্তর জমা দিয়ে আবার চেষ্টা করো।');
}

function setupReview_() {
  var sh = findResponsesSheet_();
  if (!sh) return false;
  var lastCol = sh.getLastColumn();
  var header = sh.getRange(1, 1, 1, lastCol).getValues()[0];
  if (header.indexOf(REV.status) === -1) {
    var extra = [REV.status, REV.date, REV.note, REV.exported];
    sh.getRange(1, lastCol + 1, 1, extra.length).setValues([extra]).setFontWeight('bold').setBackground('#FFE0B2');
    var statusCol = lastCol + 1;
    var rule = SpreadsheetApp.newDataValidation().requireValueInList([ST_PENDING, ST_APPROVED, ST_REJECTED], true).setAllowInvalid(false).build();
    sh.getRange(2, statusCol, 1000, 1).setDataValidation(rule);
    sh.setFrozenRows(1);
  }
  return true;
}

// ---------------------------------------------------------------- খাঁটি যুক্তি (পরীক্ষাযোগ্য)

/** ফোন নম্বর পরিষ্কার: স্পেস বাদ, বাংলা অঙ্ক → ইংরেজি, +880/880 → 0, শুরুর 0 কাটা গেলে ফেরানো। */
function normalizePhone_(raw) {
  var p = String(raw == null ? '' : raw).trim().replace(/\s+/g, '');
  var bn = '০১২৩৪৫৬৭৮৯';
  p = p.replace(/[০-৯]/g, function (c) { return String(bn.indexOf(c)); });
  p = p.replace(/^\+?880(?=1[3-9]\d{8}$)/, '0');
  if (/^1[3-9]\d{8}$/.test(p)) p = '0' + p;
  return p;
}

function validPhone_(p) {
  return /^[0-9+\-]{3,20}$/.test(p);
}

/** টেক্সট পরিষ্কার: ফর্মুলা-ইনজেকশন (=, @, + - দিয়ে শুরু) ঠেকাই, লম্বা হলে ছাঁটি। */
function clean_(s, max) {
  var t = String(s == null ? '' : s).replace(/[\r\n]+/g, ' ').replace(/\s+/g, ' ').trim();
  t = t.replace(/^[=@]+/, '').replace(/^[+\-](?!\d)/, '').trim();
  if (max && t.length > max) t = t.substring(0, max - 1) + '…';
  return t;
}

function listOf_(v) {
  return String(v == null ? '' : v).split(/\s*,\s*/).map(function (x) { return x.trim(); }).filter(Boolean);
}

/** সেবার ধরন অনুযায়ী "নোট" বানায় (শুধু প্রকাশযোগ্য তথ্য; লাইসেন্স নম্বর ইত্যাদি নয়)। */
function buildNote_(cat, a) {
  var parts = [];
  function add(x) { if (x) parts.push(x); }
  if (cat === 'হাসপাতাল') {
    add(a[Q.h_type]);
    if (a[Q.h_er] === 'হ্যাঁ') add('২৪ ঘণ্টা জরুরি বিভাগ');
    var sv = listOf_(a[Q.h_services]); if (sv.length) add('সেবা: ' + sv.join(', '));
  } else if (cat === 'এ্যাম্বুলেন্স') {
    var ty = listOf_(a[Q.a_type]); if (ty.length) add(ty.join(', '));
    if (a[Q.a_24h] === 'হ্যাঁ') add('২৪ ঘণ্টা সেবা');
    if (a[Q.a_area]) add('এলাকা: ' + a[Q.a_area]);
  } else if (cat === 'রেন্ট-এ-কার') {
    var rt = listOf_(a[Q.r_types]); if (rt.length) add(rt.join(', '));
    if (a[Q.r_driver]) add(a[Q.r_driver]);
    if (a[Q.r_area]) add('এলাকা: ' + a[Q.r_area]);
  } else if (cat === 'আইনজীবী') {
    add(a[Q.l_kind]);
    var lf = listOf_(a[Q.l_fields]); if (lf.length) add('ক্ষেত্র: ' + lf.join(', '));
  } else if (cat === 'জরুরি বিদ্যুৎ') {
    add(a[Q.e_kind]);
    var es = listOf_(a[Q.e_services]); if (es.length) add(es.join(', '));
    if (a[Q.e_24h] === 'হ্যাঁ') add('২৪ ঘণ্টা অভিযোগ গ্রহণ');
  }
  if (a[Q.hours]) add('সময়: ' + a[Q.hours]);
  if (a[Q.link]) add(a[Q.link]);
  return clean_(parts.join(' · '), 300);
}

/**
 * একটি উত্তর (শিরোনাম → মান) থেকে CSV সারি ও বার্তা বানায়।
 * ফেরত: { rows: [[৯টি কলাম], ...], messages: ['...'], problems: ['...'] }
 */
function buildRecords_(a, verifiedDate) {
  var out = { rows: [], messages: [], problems: [] };
  var request = String(a[Q.request] || '').trim();
  var catLabel = String(a[Q.category] || '').trim();
  var cat = CATEGORY_MAP[catLabel];
  var upazila = String(a[Q.upazila] || '').trim();
  var name = clean_(a[Q.name], 100);
  if (!cat) { out.problems.push('সেবার ধরন বোঝা যায়নি: ' + catLabel); return out; }
  if (UPAZILA_CHOICES.indexOf(upazila) === -1) { out.problems.push('উপজেলা বোঝা যায়নি: ' + upazila); return out; }
  if (!name) { out.problems.push('নাম নেই'); return out; }

  if (request === REQ_REMOVE) {
    out.messages.push('🗑 সরাতে হবে: "' + name + '" (' + upazila + ' / ' + cat + ')। data.csv তে সারিটা খুঁজে মুছে দাও বা "দেখাবে?" এ "না" লেখো।');
    return out;
  }
  if (request === REQ_EDIT) {
    out.messages.push('✏ সংশোধন: "' + name + '" (' + upazila + ' / ' + cat + ')। data.csv তে পুরনো সারিটা মুছে নিচের নতুন সারি বসাও।');
  }

  var phone = normalizePhone_(a[Q.phone]);
  if (!validPhone_(phone)) { out.problems.push('"' + name + '": ফোন নম্বর ঠিক নয় → ' + a[Q.phone]); return out; }
  var address = clean_(a[Q.address], 200);
  var note = buildNote_(cat, a);
  out.rows.push([upazila, cat, name, address, phone, note, 'হ্যাঁ', '', verifiedDate]);

  var phone2 = normalizePhone_(a[Q.phone2]);
  if (phone2) {
    if (validPhone_(phone2) && phone2 !== phone) {
      out.rows.push([upazila, cat, name + ' (বিকল্প নম্বর)', address, phone2, note, 'হ্যাঁ', '', verifiedDate]);
    } else if (!validPhone_(phone2)) {
      out.messages.push('⚠ "' + name + '": বিকল্প নম্বর ঠিক নয় (বাদ দেওয়া হয়েছে) → ' + a[Q.phone2]);
    }
  }
  return out;
}

function csvEscape_(v) {
  var s = String(v == null ? '' : v);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

function toCsv_(rows) {
  return rows.map(function (r) { return r.map(csvEscape_).join(','); }).join('\n');
}

// ---------------------------------------------------------------- CSV এ নেওয়া

function exportApproved() {
  var sh = findResponsesSheet_();
  if (!sh) { ui_('উত্তরের শীট পাওয়া যায়নি।'); return; }
  var data = sh.getDataRange().getValues();
  var headers = data[0];
  function col(title) { return headers.indexOf(title); }
  var iStatus = col(REV.status), iDate = col(REV.date), iExp = col(REV.exported);
  if (iStatus === -1 || iExp === -1) { ui_('রিভিউ কলাম নেই। আগে মেনু থেকে "২. রিভিউ কলাম ঠিক করো" চালাও।'); return; }

  var today = Utilities.formatDate(new Date(), 'Asia/Dhaka', 'yyyy-MM-dd');
  var rows = [], messages = [], problems = [], doneRows = [];
  for (var r = 1; r < data.length; r++) {
    var row = data[r];
    if (String(row[iStatus]).trim() !== ST_APPROVED) continue;
    if (String(row[iExp]).trim() !== '') continue;               // আগেই নেওয়া হয়েছে
    var a = {};
    for (var c = 0; c < headers.length; c++) a[headers[c]] = row[c];
    var vd = row[iDate];
    var verified = vd instanceof Date ? Utilities.formatDate(vd, 'Asia/Dhaka', 'yyyy-MM-dd') : (String(vd).trim() || today);
    var res = buildRecords_(a, verified);
    res.problems.forEach(function (p) { problems.push('সারি ' + (r + 1) + ': ' + p); });
    if (res.problems.length) continue;                            // সমস্যা থাকলে এই সারি এখন নয়
    rows = rows.concat(res.rows);
    messages = messages.concat(res.messages);
    doneRows.push(r + 1);
  }

  if (!doneRows.length && !problems.length) { ui_('নতুন কোনো "অনুমোদিত" সারি নেই।'); return; }

  // শীটে লিখি
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var out = ss.getSheetByName('CSV_Export') || ss.insertSheet('CSV_Export');
  out.clear();
  out.getRange(1, 1, 1, CSV_HEADER.length).setValues([CSV_HEADER]).setFontWeight('bold');
  if (rows.length) out.getRange(2, 1, rows.length, CSV_HEADER.length).setNumberFormat('@').setValues(rows);

  doneRows.forEach(function (rw) { sh.getRange(rw, iExp + 1).setValue(today); });

  // কপির জন্য ডায়ালগ
  var text = toCsv_(rows);
  var html = '<div style="font-family:sans-serif;font-size:13px">' +
    '<p><b>' + rows.length + 'টি সারি তৈরি।</b> নিচের লেখা কপি করে data.csv এর শেষে বসাও (হেডার ছাড়া)।</p>' +
    (messages.length ? '<p style="color:#B71C1C">' + messages.join('<br>').replace(/</g, '&lt;') + '</p>' : '') +
    (problems.length ? '<p style="color:#E65100"><b>সমস্যা (এগুলো নেওয়া হয়নি):</b><br>' + problems.join('<br>').replace(/</g, '&lt;') + '</p>' : '') +
    '<textarea style="width:100%;height:220px" onclick="this.select()">' + text.replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</textarea>' +
    '<p>একই সারিগুলো "CSV_Export" ট্যাবেও আছে (File → Download → CSV)।</p></div>';
  try {
    SpreadsheetApp.getUi().showModalDialog(HtmlService.createHtmlOutput(html).setWidth(720).setHeight(520), 'data.csv এর জন্য সারি');
  } catch (e) {
    Logger.log(text);
  }
}

// ---------------------------------------------------------------- নতুন জমার ইমেইল

function installNotify() {
  var props = PropertiesService.getDocumentProperties();
  var id = props.getProperty('formId');
  if (!id) { ui_('আগে ফর্ম তৈরি করো।'); return; }
  var existing = ScriptApp.getProjectTriggers().filter(function (t) { return t.getHandlerFunction() === 'onFormSubmitNotify'; });
  if (existing.length) { ui_('ইমেইল-বিজ্ঞপ্তি আগেই চালু আছে।'); return; }
  ScriptApp.newTrigger('onFormSubmitNotify').forForm(FormApp.openById(id)).onFormSubmit().create();
  ui_('✅ চালু হয়েছে। নতুন তথ্য জমা পড়লে তোমার ইমেইলে খবর আসবে।');
}

function onFormSubmitNotify(e) {
  var props = PropertiesService.getDocumentProperties();
  var name = '';
  try {
    e.response.getItemResponses().forEach(function (ir) {
      if (ir.getItem().getTitle() === Q.name) name = String(ir.getResponse());
    });
  } catch (err) { /* নাম না পেলেও খবর পাঠাই */ }
  MailApp.sendEmail(Session.getEffectiveUser().getEmail(),
    'ভোলা সেবা: নতুন তথ্য জমা পড়েছে' + (name ? ' - ' + name : ''),
    'যাচাই করতে শীট খোলো:\n' + (props.getProperty('sheetUrl') || ''));
}
