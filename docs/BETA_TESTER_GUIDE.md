# RigCheck tester guide

Thank you for testing RigCheck. It checks whether your truck and trailer weights add up before you tow. You are among the first few people to use it, so expect rough edges. Your job is to use it the way you normally would and tell us what looks wrong, confusing or broken.

## Where to find it

- **On the web:** https://rigcheck-web.pages.dev (any phone or computer browser).
- **On Android:** you were sent an app file ending in `.apk`. Install steps are below.

The web site can change under you without warning, because it updates whenever a new version is published. If something that worked a minute ago behaves differently, that is why. Tell us if it looks like a mistake.

## Installing the Android app

The app comes as a file instead of from the Play Store, so Android will ask you to allow it once.

1. **If you ever installed an earlier test ("debug") build of RigCheck, uninstall it first.** The beta file you were sent is signed with a different key, so Android refuses to install it over the old one. (If you never had RigCheck on that phone, skip this step.)
2. Open the `.apk` file on your phone (from the email, message or download).
3. Android will say it cannot install apps from this source. Tap **Settings**, switch on **Allow from this source** for the app you opened the file from (for example your email app or your browser), then go back.
4. Tap **Install**, then **Open**.
5. There is no automatic update. When a new version is ready we will send you a new file; install it the same way (this time you do not need to uninstall first).

## Making an account

You can use the weight check without an account. An account is needed to scan documents and to buy anything.

1. Open the sign-in screen (on the web, **Sign in** at the top of the page; in the Android app, its sign-in or account screen).
2. Choose **Create an account**, enter your email and a password, and submit.
3. **Check your email for a confirmation message and open its link.** Look in your spam folder if it does not arrive within a few minutes. Confirm before you try to sign in.
4. Come back to the app and sign in. You can also use **Continue with Google** if we added your Gmail address as a tester.

The same account works on the web and on Android, and your saved trucks and past checks should show up on both.

## What is fake

**Every purchase is a test purchase. No real money moves, and you must never enter a real card.** Pro and the scan packs are on sale so you can try buying them, but nothing you buy is real.

- **On the web**, the checkout only accepts test cards. The purchase screens are marked **Beta: test payments**.
  - Test card number: `4242 4242 4242 4242`
  - Expiry: any date in the future (for example `12/34`)
  - CVC: any three digits
  - Postal code: any valid one
  - To see what a failed payment looks like, use `4000 0000 0000 0002` (declined), `4000 0000 0000 9995` (insufficient funds) or `4000 0000 0000 0127` (wrong CVC), with the same expiry and CVC rules.
- **On Android**, purchases go through a test store instead of Google Play. Follow what the screen shows; the card numbers above are for the web checkout. Nothing is charged.

Pro gives you a larger Garage and History plus a starter bundle of scans; scan packs add more scans only. The prices, the size of the scan packs and the limits (Free: 5 saved trucks and 10 saved checks; Pro: 25 and 50) are placeholders and will change before the real launch.

## What RigCheck is not

RigCheck is an educational tool. Its results are estimates, not certified DOT weights, and it is not a certified safety decision. Do not use it as the only reason to decide a load is safe. Weigh your rig on a certified scale if it matters.

## What is not in this test yet

So you do not waste time looking for it:

- **No real payments, no refunds and no legal terms yet.** Android has no Google Play billing at all in this test; it uses a test store.
- **No Garage upgrade offer and no fleet management** (managing several trucks as a business).
- **No privacy page or terms page yet.** See the privacy note below.
- **No iPhone app** and no "Sign in with Apple".
- **Android does not copy trucks you saved on the phone before signing in.** If you saved a truck while signed out and then sign in, it will seem to disappear from the list. It is not copied into your account. (The web site does copy them.)
- **Android has no History filters yet.** The web site does.
- **Only fifth-wheel and gooseneck trailers.** Bumper-pull trailers (the kind that hitch to a ball and have tongue weight) are not supported.
- **No way to delete your account inside the app.** See the privacy note below.
- **No limit on how many scans one account can make.** Please scan sensibly; each scan costs us a little.
- **The free storage we use can pause** after a quiet week or lose data, since there are no backups. If sign-in suddenly fails for everyone, tell us.
- **No security or code review has been done yet.** The app runs as it stands today.
- **The older demo site** is not part of this test.

## Privacy

When you scan a photo (a truck tag, a weigh ticket, a document), the photo is sent to Anthropic, the company that makes Claude, so that it can be read, and the numbers it finds are sent back to you. There is no privacy page yet. If you want your account and its saved data deleted, ask us by email at WTIAppDev@gmail.com and we will do it; you cannot do it inside the app yet.

## What to try

You do not need to do all of these. Do what you would do with the app anyway, and try the odd things too.

- Create an account with your email and confirm it. (If you have a Gmail address we added, also try **Continue with Google**.)
- Reset your password from the sign-in screen.
- Run a weight check without signing in, then another while signed in.
- Save a truck and trailer to your Garage and use it again for a second check.
- Scan each kind of document: the truck tag, the trailer tag and the weigh ticket. (Only accounts with Pro can scan.)
- Buy Pro with the test card, and also start a purchase and cancel it. (If we left you on the free plan, this is your job; Pro cannot be bought twice.)
- Buy a scan pack with the test card. (After you have Pro.)
- Open the same account on the web and on Android and compare your Garage and History.
- Look at a result that is over the limit and one that is within it, and check that the wording makes sense.
- Sign out and sign back in.
- Anything that looks wrong, confusing, ugly or slow.

## How to report a problem

Email **WTIAppDev@gmail.com**. In the web app, the **Send feedback** link (in the page footer and on your Account screen) opens an email to that address for you.

A good report says: what you were doing, what you expected, what happened instead, and whether it was on the web or Android (and which phone). A screenshot helps a lot. Do not send your password.

If the Android app closes by itself, the next time you open it asks "RigCheck closed unexpectedly last time. Send details?". This is optional: **Send** opens an email to us with the details (the error, the app version, your Android version and your phone model; nothing about your account or your rigs) for you to look over and send, and **Not now** deletes them. Nothing is sent unless you send that email.
