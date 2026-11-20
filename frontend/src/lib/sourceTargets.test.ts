import { describe, expect, it } from 'vitest';
import { movableTargets, sourceName } from './sourceTargets';
import type { Source } from './types';

const source = (id: number, writable: boolean, label: string | null = null): Source => ({
	id,
	path: `/srv/${id}`,
	label,
	recursive: true,
	enabled: true,
	writable,
	rename_to_hash: false,
	created_at: '2024-01-01T00:00:00',
	last_scan: null
});

describe('movableTargets', () => {
	it('leaves out the source the files come from', () => {
		expect(movableTargets([source(1, true), source(2, true)], 1).map((s) => s.id)).toEqual([2]);
	});

	it('leaves out read-only sources', () => {
		const sources = [source(1, true), source(2, false), source(3, true)];
		expect(movableTargets(sources, 1).map((s) => s.id)).toEqual([3]);
	});
});

describe('sourceName', () => {
	it('prefers the label, and falls back to the folder', () => {
		expect(sourceName(source(1, true, 'Generations'))).toBe('Generations');
		expect(sourceName(source(1, true))).toBe('/srv/1');
	});
});
