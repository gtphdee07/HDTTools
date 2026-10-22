// Read-only check (#146) that the RevenueCat entitlement the sites gate Pro on exists
// and has the Pro product the Web paywall sells attached to it. A promotional grant
// makes the entitlement active whether or not any product maps to it, so the Web
// External suite cannot see a detached entitlement; the project configuration can.
// Used only by the External suite (revenuecatRest.external.test.ts): it makes GET
// requests with a project-configuration read key and never writes. Every failure
// message names what is missing, so the dashboard fix is obvious.
const API_BASE = "https://api.revenuecat.com/v2";
const TIMEOUT_MS = 10_000;
const PAGE_LIMIT = 100;
const MAX_PAGES = 20;

// The read key this check needs; separate from the ledger's REVENUECAT_SECRET_KEY (#146 decision 1).
export const CONFIG_READ_KEY_VAR = "REVENUECAT_CONFIG_READ_KEY";

export interface ProAttachmentCheck {
  apiKey: string;
  projectId: string;
  entitlementKey: string;
  offeringKey: string;
  packageKey: string;
}

interface Product {
  id: string;
  app_id?: string;
  store_identifier?: string;
}

const describe = (product: Product) => `${product.id} (${product.store_identifier ?? "no store id"})`;

// Every item of a list endpoint, following pagination. 401/403 means the key, not the
// project, is at fault, so it names the call and the permission to add.
async function listAll<T>(check: ProAttachmentCheck, path: string, permission: string): Promise<T[]> {
  const items: T[] = [];
  let after: string | undefined;
  for (let page = 0; page < MAX_PAGES; page++) {
    const query = new URLSearchParams({ limit: String(PAGE_LIMIT) });
    if (after) query.set("starting_after", after);
    const res = await fetch(`${API_BASE}/projects/${check.projectId}${path}?${query}`, {
      headers: { Authorization: `Bearer ${check.apiKey}` },
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const body = (await res.json().catch(() => null)) as { items?: T[]; next_page?: string | null } | null;
    if (res.status === 401 || res.status === 403) {
      throw new Error(
        `GET ${path} was rejected (${res.status}): ${CONFIG_READ_KEY_VAR} is wrong or lacks the ` +
          `${permission} permission (a v2 secret key with read access to project configuration): ${JSON.stringify(body)}`,
      );
    }
    if (!res.ok || !Array.isArray(body?.items)) {
      throw new Error(`GET ${path} answered ${res.status} without a list: ${JSON.stringify(body)}`);
    }
    items.push(...body.items);
    const last = body.items[body.items.length - 1] as { id?: string; product?: { id: string } } | undefined;
    after = last?.id ?? last?.product?.id;
    if (!body.next_page || !after) return items;
  }
  throw new Error(`GET ${path} did not finish paging after ${MAX_PAGES} pages`);
}

export async function checkProAttachment(check: ProAttachmentCheck): Promise<void> {
  const { entitlementKey, offeringKey, packageKey } = check;

  const entitlements = await listAll<{ id: string; lookup_key: string }>(
    check,
    "/entitlements",
    "project_configuration:entitlements:read",
  );
  const entitlement = entitlements.find((e) => e.lookup_key === entitlementKey);
  if (!entitlement) {
    throw new Error(
      `entitlement "${entitlementKey}" does not exist in RevenueCat project ${check.projectId} ` +
        `(found: ${entitlements.map((e) => e.lookup_key).join(", ") || "none"}): create it under Product catalog > Entitlements`,
    );
  }
  const attached = await listAll<Product>(
    check,
    `/entitlements/${entitlement.id}/products`,
    "project_configuration:entitlements:read",
  );
  if (attached.length === 0) {
    throw new Error(
      `entitlement "${entitlementKey}" exists but has no product attached: attach the Pro product ` +
        `under Product catalog > Entitlements > ${entitlementKey} > Attach`,
    );
  }

  const offerings = await listAll<{ id: string; lookup_key: string }>(
    check,
    "/offerings",
    "project_configuration:offerings:read",
  );
  const offering = offerings.find((o) => o.lookup_key === offeringKey);
  if (!offering) {
    throw new Error(
      `offering "${offeringKey}" (the one the Web paywall reads) does not exist ` +
        `(found: ${offerings.map((o) => o.lookup_key).join(", ") || "none"})`,
    );
  }
  const packages = await listAll<{ id: string; lookup_key: string }>(
    check,
    `/offerings/${offering.id}/packages`,
    "project_configuration:packages:read",
  );
  const pkg = packages.find((p) => p.lookup_key === packageKey);
  if (!pkg) {
    throw new Error(
      `package "${packageKey}" does not exist in offering "${offeringKey}" ` +
        `(found: ${packages.map((p) => p.lookup_key).join(", ") || "none"})`,
    );
  }

  // The Web paywall buys the package's Web Billing product (the SDK's webBillingProduct).
  const [packageProducts, apps] = await Promise.all([
    listAll<{ product: Product }>(check, `/packages/${pkg.id}/products`, "project_configuration:packages:read"),
    listAll<{ id: string; type: string }>(check, "/apps", "project_configuration:apps:read"),
  ]);
  const webApps = new Set(apps.filter((a) => a.type === "rc_billing").map((a) => a.id));
  const webProducts = packageProducts.map((p) => p.product).filter((p) => p.app_id && webApps.has(p.app_id));
  if (webProducts.length === 0) {
    throw new Error(
      `package "${packageKey}" of offering "${offeringKey}" has no Web Billing product, so the Web paywall has ` +
        `nothing to sell: add the Pro product from the Web Billing app to that package`,
    );
  }

  const attachedIds = new Set(attached.map((p) => p.id));
  const detached = webProducts.filter((p) => !attachedIds.has(p.id));
  if (detached.length > 0) {
    throw new Error(
      `the Web paywall's product ${detached.map(describe).join(", ")} (package "${packageKey}" of offering ` +
        `"${offeringKey}") is not attached to entitlement "${entitlementKey}" (attached: ${attached.map(describe).join(", ")}): ` +
        `a customer who buys it would stay Free; attach it under Product catalog > Entitlements > ${entitlementKey} > Attach`,
    );
  }
}
