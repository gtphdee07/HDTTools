// Side-effect import: put it first in every top-level *.test.ts. Throws at load when the
// proxy's dependencies are missing, so the file fails with the install instruction rather
// than a downstream 502 assertion. See installGuard.ts. Also runnable directly
// (`node src/requireInstall.ts`) as the dependency check the Python tests use.
import { assertInstalled } from "./installGuard.ts";

assertInstalled();
