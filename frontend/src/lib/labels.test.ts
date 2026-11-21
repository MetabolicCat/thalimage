import { describe, expect, it } from 'vitest';
import {
	labelCounts,
	missingNamespaces,
	nextUnlabelled,
	toggleLabel,
	vocabularyLabels,
	type Namespace
} from './labels';

const VOCAB: Namespace[] = [
	{ name: 'medium', multiple: false, values: ['photographic', 'pixel'] },
	{ name: 'overlay', multiple: true, values: ['none', 'anime', 'cinematic'] }
];

// The vocabulary's `rating` namespace shares its prefix with the star
// ratings a scan imports (`rating:1` … `rating:5`).
const RATED: Namespace[] = [
	...VOCAB,
	{ name: 'rating', multiple: false, values: ['sfw', 'porn'] }
];

describe('vocabularyLabels', () => {
	it('lists every value with its namespace', () => {
		expect(vocabularyLabels(VOCAB)).toEqual([
			'medium:photographic',
			'medium:pixel',
			'overlay:none',
			'overlay:anime',
			'overlay:cinematic'
		]);
	});
});

describe('toggleLabel', () => {
	it('replaces the value of a single-valued namespace', () => {
		expect(toggleLabel(VOCAB, ['medium:pixel', 'overlay:anime'], 'medium:photographic')).toEqual({
			add: ['medium:photographic'],
			remove: ['medium:pixel']
		});
	});

	it('removes a label the image already has', () => {
		expect(toggleLabel(VOCAB, ['medium:pixel'], 'medium:pixel')).toEqual({ add: [], remove: ['medium:pixel'] });
		expect(toggleLabel(VOCAB, ['overlay:anime'], 'overlay:anime')).toEqual({ add: [], remove: ['overlay:anime'] });
	});

	it('leaves tags outside the vocabulary values alone', () => {
		expect(toggleLabel(RATED, ['rating:sfw', 'rating:3'], 'rating:porn')).toEqual({
			add: ['rating:porn'],
			remove: ['rating:sfw']
		});
		expect(toggleLabel(RATED, ['rating:sfw', 'rating:3'], 'rating:sfw')).toEqual({
			add: [],
			remove: ['rating:sfw']
		});
	});

	it('adds to a multi-valued namespace, where none excludes the others', () => {
		expect(toggleLabel(VOCAB, ['overlay:anime'], 'overlay:cinematic')).toEqual({
			add: ['overlay:cinematic'],
			remove: []
		});
		expect(toggleLabel(VOCAB, ['overlay:anime', 'overlay:cinematic'], 'overlay:none')).toEqual({
			add: ['overlay:none'],
			remove: ['overlay:anime', 'overlay:cinematic']
		});
		expect(toggleLabel(VOCAB, ['overlay:none'], 'overlay:anime')).toEqual({
			add: ['overlay:anime'],
			remove: ['overlay:none']
		});
	});
});

describe('missingNamespaces', () => {
	it('lists the namespaces without a label', () => {
		expect(missingNamespaces(VOCAB, ['overlay:none', 'other:x'])).toEqual(['medium']);
		expect(missingNamespaces(VOCAB, ['medium:pixel', 'overlay:anime'])).toEqual([]);
	});

	it('does not count a tag outside the vocabulary as its namespace', () => {
		expect(missingNamespaces(RATED, ['medium:pixel', 'overlay:anime', 'rating:3'])).toEqual([
			'rating'
		]);
	});
});

describe('labelCounts', () => {
	it('counts each label over the images', () => {
		const counts = labelCounts([
			{ content_hash: 'a', filename: 'a.png', animated: false, labels: ['medium:pixel', 'overlay:anime'] },
			{ content_hash: 'b', filename: 'b.png', animated: false, labels: ['medium:pixel'] }
		]);
		expect(counts.get('medium:pixel')).toBe(2);
		expect(counts.get('overlay:anime')).toBe(1);
		expect(counts.get('medium:photographic')).toBeUndefined();
	});
});

describe('nextUnlabelled', () => {
	const images = [
		{ content_hash: 'a', filename: 'a.png', animated: false, labels: [] },
		{ content_hash: 'b', filename: 'b.png', animated: false, labels: ['medium:pixel', 'overlay:none'] },
		{ content_hash: 'c', filename: 'c.png', animated: false, labels: ['medium:pixel'] }
	];

	it('finds the next image missing a namespace, wrapping round', () => {
		expect(nextUnlabelled(VOCAB, images, 0)).toBe(2);
		expect(nextUnlabelled(VOCAB, images, 2)).toBe(0);
	});

	it('is -1 when every image is labelled', () => {
		expect(nextUnlabelled(VOCAB, [images[1]], 0)).toBe(-1);
	});

	it('does not treat an imported star rating as the rating label', () => {
		const rated = [{ ...images[1], labels: [...images[1].labels, 'rating:3'] }];
		expect(nextUnlabelled(RATED, rated, 0)).toBe(0);
	});
});
