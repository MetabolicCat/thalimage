import type { ImageCopy, ImageDeletion, SourceMove } from './types';

/** The copy's full path on the server. */
export function copyPath(copy: ImageCopy): string {
	return `${copy.source_path.replace(/\/+$/, '')}/${copy.relative_path}`;
}

/** Folders of the sources holding a copy that Thalimage may not change. */
export function readOnlySources(copies: ImageCopy[]): string[] {
	return [...new Set(copies.filter((c) => !c.writable).map((c) => c.source_path))];
}

/** The copy once renamed to the image's hash: same folder, extension as found. */
export function hashNamed(copy: ImageCopy, hash: string): ImageCopy {
	const slash = copy.relative_path.lastIndexOf('/');
	const folder = copy.relative_path.slice(0, slash + 1);
	const name = copy.relative_path.slice(slash + 1);
	const dot = name.lastIndexOf('.');
	const extension = dot > 0 ? name.slice(dot) : '';
	return { ...copy, relative_path: `${folder}${hash}${extension}` };
}

/** The files a delete left on disk, and why; empty when it removed them all. */
export function deletionFailures(result: ImageDeletion): string {
	if (result.failed.length === 0) return '';
	return (
		`Deleted ${result.deleted}; these could not be deleted: ` +
		result.failed.map((f) => `${f.relative_path} (${f.error})`).join(', ')
	);
}

/** The files a move to another source left behind, and why; empty when every
 * file moved. */
export function moveFailures(result: SourceMove): string {
	if (result.failed.length === 0) return '';
	return (
		`Moved ${result.moved.length + result.deleted.length}; these could not be moved: ` +
		result.failed.map((f) => `${f.relative_path} (${f.error})`).join(', ')
	);
}
