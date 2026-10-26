/**
 * মেনু: একই Google Sheet/প্রজেক্টে FormSetup.gs, PhotoApprove.gs, SpotSetup.gs তিনটিই থাকতে পারে।
 * Apps Script-এ একটি প্রজেক্টে শুধু একটি onOpen চলে; তাই এই ফাইল থেকে সবগুলোর মেনু ডাকা হয়।
 * যে ফাইলগুলো প্রজেক্টে নেই, সেগুলোর মেনু বাদ যায় (কোনো এরর হয় না)।
 */
function onOpen() {
  if (typeof infoMenu_ === 'function') infoMenu_();    // FormSetup.gs: "ভোলা সেবা"
  if (typeof photoMenu_ === 'function') photoMenu_();  // PhotoApprove.gs: "ভোলা ছবি"
  if (typeof spotMenu_ === 'function') spotMenu_();    // SpotSetup.gs: "ভোলা স্পট"
}
