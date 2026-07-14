import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { buildAppRegistration, buildManifest, buildOpenApiDocument } from "@/lib/app-definition/contracts";
import { appDefinition } from "@/lib/app-definition/definition";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const generatedAt = new Date().toISOString();

async function writeGeneratedFile(path: string, content: string) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, content);
}

try {
  const manifest = buildManifest(appDefinition);
  const openapi = buildOpenApiDocument(appDefinition);
  const registration = buildAppRegistration(appDefinition);

  await writeGeneratedFile(join(root, "generated/manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  await writeGeneratedFile(join(root, "generated/openapi.json"), `${JSON.stringify(openapi, null, 2)}\n`);
  await writeGeneratedFile(join(root, "generated/app-registration.json"), `${JSON.stringify(registration, null, 2)}\n`);

  console.log(`Generated general website contracts at ${generatedAt}`);
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
