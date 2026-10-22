import "./requireInstall.ts";
import assert from "node:assert/strict";
import test from "node:test";
import type { TestContext } from "node:test";
import { checkProAttachment } from "./revenuecatProAttachment.ts";

// A fake RevenueCat project configuration, served by URL. Only GETs are answered, so a
// write (or any call the check should not make) fails the test.
interface Project {
  entitlements: { id: string; lookup_key: string }[];
  entitlementProducts: Record<string, string[]>; // entitlement id -> product ids
  offerings: { id: string; lookup_key: string }[];
  packages: Record<string, { id: string; lookup_key: string }[]>; // offering id -> packages
  packageProducts: Record<string, string[]>; // package id -> product ids
  products: Record<string, { app_id: string; store_identifier: string }>;
  apps: { id: string; type: string }[];
}

const WEB_PRODUCT = "prod_web";
const ANDROID_PRODUCT = "prod_android";

const healthy = (): Project => ({
  entitlements: [
    { id: "entl_other", lookup_key: "other" },
    { id: "entl_pro", lookup_key: "pro" },
  ],
  entitlementProducts: { entl_pro: [WEB_PRODUCT, ANDROID_PRODUCT], entl_other: [] },
  offerings: [{ id: "ofrng_web", lookup_key: "web" }],
  packages: { ofrng_web: [{ id: "pkg_life", lookup_key: "$rc_lifetime" }] },
  packageProducts: { pkg_life: [WEB_PRODUCT, ANDROID_PRODUCT] },
  products: {
    [WEB_PRODUCT]: { app_id: "app_web", store_identifier: "rigcheck_pro_lifetime" },
    [ANDROID_PRODUCT]: { app_id: "app_android", store_identifier: "lifetime" },
  },
  apps: [
    { id: "app_android", type: "test_store" },
    { id: "app_web", type: "rc_billing" },
  ],
});

const check = {
  apiKey: "sk_read_only",
  projectId: "proj_abc",
  entitlementKey: "pro",
  offeringKey: "web",
  packageKey: "$rc_lifetime",
};

const productBody = (id: string, project: Project) => ({ object: "product", id, ...project.products[id] });

// Serves `project` at /v2/projects/proj_abc/..., one page per request of `pageSize` items.
function serve(t: TestContext, project: Project, options: { pageSize?: number; status?: number } = {}) {
  const calls: { url: string; method: string; authorization: string | undefined }[] = [];
  t.mock.method(globalThis, "fetch", async (input: string | URL, init?: RequestInit) => {
    const url = new URL(String(input));
    calls.push({
      url: url.pathname + url.search,
      method: init?.method ?? "GET",
      authorization: (init?.headers as Record<string, string> | undefined)?.Authorization,
    });
    if (options.status) return new Response(JSON.stringify({ message: "forbidden" }), { status: options.status });
    const route = url.pathname.replace("/v2/projects/proj_abc", "");
    let items: unknown[] | undefined;
    let m: RegExpMatchArray | null;
    if (route === "/entitlements") items = project.entitlements;
    else if ((m = route.match(/^\/entitlements\/([^/]+)\/products$/))) {
      items = (project.entitlementProducts[m[1]!] ?? []).map((id) => productBody(id, project));
    } else if (route === "/offerings") items = project.offerings;
    else if ((m = route.match(/^\/offerings\/([^/]+)\/packages$/))) items = project.packages[m[1]!] ?? [];
    else if ((m = route.match(/^\/packages\/([^/]+)\/products$/))) {
      items = (project.packageProducts[m[1]!] ?? []).map((id) => ({
        product: productBody(id, project),
        eligibility_criteria: "all",
      }));
    } else if (route === "/apps") items = project.apps;
    if (!items || init?.method) return new Response("{}", { status: 404 });
    const pageSize = options.pageSize ?? 100;
    const after = url.searchParams.get("starting_after");
    const ids = items.map((item) => (item as { id?: string; product?: { id: string } }).id ?? (item as { product: { id: string } }).product.id);
    const start = after ? ids.indexOf(after) + 1 : 0;
    const page = items.slice(start, start + pageSize);
    const more = start + pageSize < items.length;
    return new Response(JSON.stringify({ object: "list", items: page, next_page: more ? "next" : null }), { status: 200 });
  });
  return calls;
}

test("passes when pro exists and the product the Web paywall sells is attached to it, using only GETs", async (t) => {
  const calls = serve(t, healthy());
  await checkProAttachment(check);
  assert.ok(calls.length > 0);
  assert.ok(calls.every((c) => c.method === "GET"), "the check must never write");
  assert.ok(calls.every((c) => c.authorization === "Bearer sk_read_only"));
});

test("follows pagination: pro on the second page of entitlements is still found", async (t) => {
  serve(t, healthy(), { pageSize: 1 });
  await checkProAttachment(check);
});

test("fails naming a missing entitlement, and lists what does exist", async (t) => {
  serve(t, healthy());
  await assert.rejects(
    checkProAttachment({ ...check, entitlementKey: "pro-typo" }),
    (e: Error) => /entitlement "pro-typo" does not exist/.test(e.message) && e.message.includes("other, pro"),
  );
});

test("fails naming an entitlement that exists with no product attached", async (t) => {
  const project = healthy();
  project.entitlementProducts.entl_pro = [];
  serve(t, project);
  await assert.rejects(checkProAttachment(check), /entitlement "pro" exists but has no product attached/);
});

test("fails when only the Android product is attached: the Web paywall's product is not", async (t) => {
  const project = healthy();
  project.entitlementProducts.entl_pro = [ANDROID_PRODUCT];
  serve(t, project);
  await assert.rejects(
    checkProAttachment(check),
    (e: Error) =>
      /not attached to entitlement "pro"/.test(e.message) &&
      e.message.includes(WEB_PRODUCT) &&
      e.message.includes("rigcheck_pro_lifetime") &&
      e.message.includes("package \"$rc_lifetime\""),
  );
});

test("fails naming a missing offering, a missing package, and a package with no Web Billing product", async (t) => {
  serve(t, healthy());
  await assert.rejects(checkProAttachment({ ...check, offeringKey: "nope" }), /offering "nope" .* does not exist \(found: web\)/);
  await assert.rejects(
    checkProAttachment({ ...check, packageKey: "$rc_annual" }),
    /package "\$rc_annual" does not exist in offering "web"/,
  );

  const project = healthy();
  project.packageProducts.pkg_life = [ANDROID_PRODUCT];
  serve(t, project);
  await assert.rejects(checkProAttachment(check), /package "\$rc_lifetime" .* has no Web Billing product/);
});

test("a server error or a non-list answer names the call and status instead of a confusing 'does not exist'", async (t) => {
  serve(t, healthy(), { status: 500 });
  await assert.rejects(checkProAttachment(check), /GET \/entitlements answered 500 without a list/);
});

test("a rejected key names the call, the key variable and the permission, never the key", async (t) => {
  serve(t, healthy(), { status: 403 });
  await assert.rejects(checkProAttachment(check), (e: Error) => {
    assert.match(e.message, /REVENUECAT_CONFIG_READ_KEY/);
    assert.match(e.message, /403/);
    assert.match(e.message, /project_configuration:entitlements:read/);
    assert.ok(!e.message.includes("sk_read_only"));
    return true;
  });
});
