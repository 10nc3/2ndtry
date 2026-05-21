import "./agent-scope-DMMelGwC.js";
import { c as resolveDefaultAgentId, o as resolveAgentWorkspaceDir } from "./agent-scope-config-DCRwWQZy.js";
import { i as loadPluginMetadataSnapshot } from "./plugin-metadata-snapshot-yo9-w2SZ.js";
import { b as setCurrentPluginMetadataSnapshot, v as getCurrentPluginMetadataSnapshot } from "./plugin-registry-BZohWtpt.js";
import { t as createSubsystemLogger } from "./subsystem-C-H8Q21Y.js";
import { i as getRuntimeConfig } from "./io-CiCdMMvQ.js";
import "./config-ClOrPUuZ.js";
import { t as applyPluginAutoEnable } from "./plugin-auto-enable-Ca3CdPro.js";
import { E as resolvePluginActivationSourceConfig } from "./loader-CZB9kQVT.js";
import "./logging-BFdm3vtw.js";
//#region src/plugins/runtime/load-context.ts
const log = createSubsystemLogger("plugins");
function createPluginRuntimeLoaderLogger() {
	return {
		info: (message) => log.info(message),
		warn: (message) => log.warn(message),
		error: (message) => log.error(message),
		debug: (message) => log.debug(message)
	};
}
function resolvePluginRuntimeLoadContext(options) {
	const env = options?.env ?? process.env;
	const rawConfig = options?.config ?? getRuntimeConfig();
	const rawWorkspaceDir = options?.workspaceDir ?? resolveAgentWorkspaceDir(rawConfig, resolveDefaultAgentId(rawConfig));
	const metadataSnapshot = options?.manifestRegistry ? void 0 : getCurrentPluginMetadataSnapshot({
		config: rawConfig,
		env,
		workspaceDir: rawWorkspaceDir
	}) ?? loadPluginMetadataSnapshot({
		config: rawConfig,
		env,
		workspaceDir: rawWorkspaceDir
	});
	const manifestRegistry = options?.manifestRegistry ?? metadataSnapshot?.manifestRegistry;
	const activationSourceConfig = resolvePluginActivationSourceConfig({
		config: rawConfig,
		activationSourceConfig: options?.activationSourceConfig
	});
	const autoEnabled = applyPluginAutoEnable({
		config: rawConfig,
		env,
		manifestRegistry
	});
	const config = autoEnabled.config;
	const workspaceDir = options?.workspaceDir ?? resolveAgentWorkspaceDir(config, resolveDefaultAgentId(config));
	if (metadataSnapshot) setCurrentPluginMetadataSnapshot(metadataSnapshot, {
		config: rawConfig,
		compatibleConfigs: [config, activationSourceConfig],
		env,
		workspaceDir
	});
	return {
		rawConfig,
		config,
		activationSourceConfig,
		autoEnabledReasons: autoEnabled.autoEnabledReasons,
		workspaceDir,
		env,
		logger: options?.logger ?? createPluginRuntimeLoaderLogger(),
		...manifestRegistry ? { manifestRegistry } : {}
	};
}
function buildPluginRuntimeLoadOptions(context, overrides) {
	return buildPluginRuntimeLoadOptionsFromValues(context, overrides);
}
function buildPluginRuntimeLoadOptionsFromValues(values, overrides) {
	return {
		config: values.config,
		activationSourceConfig: values.activationSourceConfig,
		autoEnabledReasons: values.autoEnabledReasons,
		workspaceDir: values.workspaceDir,
		env: values.env,
		logger: values.logger,
		...values.manifestRegistry ? { manifestRegistry: values.manifestRegistry } : {},
		...overrides
	};
}
//#endregion
export { resolvePluginRuntimeLoadContext as i, buildPluginRuntimeLoadOptionsFromValues as n, createPluginRuntimeLoaderLogger as r, buildPluginRuntimeLoadOptions as t };
