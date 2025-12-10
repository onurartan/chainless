// AUTO GENERATED FILE - DO NOT EDIT
//
// This file is auto-generated from your environment schema (.envx).
// It defines the TypeScript interface for your environment variables,
// allowing you to use it with getEnvx or similar functions to get
// fully typed and validated environment configs.
//
// Usage example:
//
// import { getEnv } from "typenvx";
// import type { EnvVars } from "./envx.ts";
//
// const env = getEnv<EnvVars>();
// console.log(env.API_URL); // typed as string
//
// NOTE:
// - Optional variables are marked with '?'.
// - Enum variables are typed as string literals.
//
// Keep this file updated by regenerating after schema changes.

export interface EnvVars {
  DEVELOPER_MESSAGE: string;
  PROD_BASE_URL: string;
  NODE_ENV?: string;
  DEV_MODE?: string;
  GITHUB_REPO_NAME?: string;
  GITHUB_REPO_USERNAME?: string;
  GITHUB_REPO_URL?: string;
  TRYMAGIC_URL?: string;
  BASE_URL?: string;
  CHAINLESS_TEXT?: string;
}
