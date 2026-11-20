/** Video file extensions; must match VIDEO_EXTENSIONS in backend core/video.py. */
const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.webm', '.avi', '.mkv']);

/** Whether a filename is one of the video formats the scanner indexes. */
export function isVideoFilename(filename: string): boolean {
	const dot = filename.lastIndexOf('.');
	return dot >= 0 && VIDEO_EXTENSIONS.has(filename.slice(dot).toLowerCase());
}

/**
 * Whether a filename is a GIF. The viewer sends these whole rather than as a
 * WebP preview, because the preview would show only the first frame.
 */
export function isGifFilename(filename: string): boolean {
	const dot = filename.lastIndexOf('.');
	return dot >= 0 && filename.slice(dot).toLowerCase() === '.gif';
}
