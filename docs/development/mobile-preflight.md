# Native mobile preflight

Run from a clean OffMenu checkout with Node. No SDK install, device, account,
network, or signing material is required for these commands:

    node scripts/mobile-preflight.mjs
    node --test tests/web/mobile-preflight.test.mjs

Host output distinguishes unsupported local hosts, missing tools, Linux KVM
access not verified, and executables present but unverified. This does not run
an SDK, compile an app, enumerate devices, or account for hosted quota. The
Android SDK locator checks PATH and standard ANDROID_HOME/ANDROID_SDK_ROOT
locations. On macOS an Xcode shim alone is not evidence of a simulator runtime.

A future authorized build lane can pass a local JSON receipt and exact revision:

    node scripts/mobile-preflight.mjs "$(git rev-parse HEAD)" "$(git rev-parse HEAD^{tree})" receipt.json

The envelope uses schema offmenu.native-preflight/1, source {commit, tree}, and
records with optional android and ios keys. Each recorded platform must start
with a passing compile object containing the same commit and tree, artifact,
artifactSha256, and a toolchainPin. Android artifact is debug-apk; iOS artifact
is unsigned-simulator-app. Optional passing install repeats commit, tree and
artifactSha256, and adds target (android-emulator or ios-simulator),
simulatorId and runtimePin. A passing journey repeats those hashes, simulatorId
and runtimePin, adds driver (android-instrumentation or xcuitest),
reportSha256, and nonempty unique case names. Use synthetic or ephemeral
simulator IDs, not physical-device serials or secrets.

The verifier checks receipt shape and consistency, not issuer authenticity,
actual report bytes, behavior or full journey coverage. WebView-only script
execution does not count as a native journey. Report unrun cases, artifacts
and actual device/store checks separately. No native packaging, signing, store
upload, hosted runner, quota, or paid plan is configured by this preflight.
