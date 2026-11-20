import { describe, expect, it } from 'vitest';
import { returnToHref, settingsHref } from './settingsLink';

describe('settingsHref', () => {
	it('returns to the current page, query included', () => {
		expect(settingsHref(new URL('http://x/collections/3?sort=name'))).toBe(
			'/settings?returnTo=%2Fcollections%2F3%3Fsort%3Dname'
		);
	});

	it('does not point Settings back at itself', () => {
		expect(settingsHref(new URL('http://x/settings?returnTo=%2F'))).toBe('/settings');
	});
});

describe('returnToHref', () => {
	const page = (returnTo: string) =>
		new URL(`http://x/settings?returnTo=${encodeURIComponent(returnTo)}`);

	it('round-trips a path on this origin, query and fragment included', () => {
		expect(returnToHref(page('/collections/3?sort=name#top'))).toBe(
			'/collections/3?sort=name#top'
		);
	});

	it('defaults to the gallery without a returnTo', () => {
		expect(returnToHref(new URL('http://x/settings'))).toBe('/');
	});

	it.each([
		'javascript:alert(1)',
		'//evil.example',
		'/\\evil.example',
		'https://evil.example',
		'evil.example',
		''
	])('refuses the off-origin value %j', (value) => {
		expect(returnToHref(page(value))).toBe('/');
	});
});
