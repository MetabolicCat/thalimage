import { describe, expect, it } from 'vitest';
import { isGifFilename, isVideoFilename } from './media';

describe('isVideoFilename', () => {
	it('recognises video extensions in any case', () => {
		for (const name of ['a.mp4', 'b.MOV', 'c.webm', 'clip.final.avi', 'd.mkv']) {
			expect(isVideoFilename(name)).toBe(true);
		}
	});

	it('rejects stills and extension-less names', () => {
		for (const name of ['a.png', 'mp4', 'movie.mp4.png', '']) {
			expect(isVideoFilename(name)).toBe(false);
		}
	});
});

describe('isGifFilename', () => {
	it('recognises GIF in any case', () => {
		for (const name of ['a.gif', 'A.GIF', 'clip.final.Gif']) {
			expect(isGifFilename(name)).toBe(true);
		}
	});

	it('rejects other images and extension-less names', () => {
		for (const name of ['a.png', 'a.webp', 'gif', 'movie.gif.png', '']) {
			expect(isGifFilename(name)).toBe(false);
		}
	});
});
