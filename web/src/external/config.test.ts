import { describe, expect, it } from 'vitest';
import { REQUIRED, readConfig } from './config';

const full = {
  VITE_SUPABASE_URL: 'https://example-url.invalid',
  VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_SECRETKEY',
  WEB_EXTERNAL_TEST_EMAIL: 'secret-person@example.invalid',
  WEB_EXTERNAL_TEST_PASSWORD: 'SECRETPASSWORD',
};

describe('readConfig', () => {
  it('returns every value when all are present', () => {
    expect(readConfig(full)).toEqual(full);
  });

  it.each(REQUIRED)('throws when %s is missing', (name) => {
    expect(() => readConfig({ ...full, [name]: undefined })).toThrow(name);
  });

  it.each(REQUIRED)('treats an empty %s as missing', (name) => {
    expect(() => readConfig({ ...full, [name]: '' })).toThrow(name);
  });

  it('names every missing variable', () => {
    expect(() => readConfig({})).toThrow(new RegExp(REQUIRED.join('.*')));
  });

  it('checks only the named variables when given a subset', () => {
    const subset = ['VITE_SUPABASE_URL', 'VITE_SUPABASE_PUBLISHABLE_KEY'] as const;
    const env = { VITE_SUPABASE_URL: 'https://a.invalid', VITE_SUPABASE_PUBLISHABLE_KEY: 'k' };
    expect(readConfig(env, subset)).toEqual(env);
    expect(() => readConfig({ VITE_SUPABASE_URL: 'https://a.invalid' }, subset)).toThrow('VITE_SUPABASE_PUBLISHABLE_KEY');
    expect(() => readConfig({ VITE_SUPABASE_URL: 'https://a.invalid' }, subset)).not.toThrow('WEB_EXTERNAL_TEST_EMAIL');
  });

  it('never includes a value in the message', () => {
    let message = '';
    try {
      readConfig({ ...full, WEB_EXTERNAL_TEST_EMAIL: undefined });
    } catch (e) {
      message = (e as Error).message;
    }
    expect(message).not.toBe('');
    for (const value of Object.values(full)) expect(message).not.toContain(value);
  });
});
