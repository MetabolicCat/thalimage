/**
 * Labelling a set of images by hand with namespaced tags
 * (`medium:photographic`), for measuring the auto-tagging models (#164).
 */

export interface Namespace {
	name: string;
	/** Several values at once; then `none` says the image has none of them. */
	multiple: boolean;
	values: string[];
}

export interface ImageLabels {
	content_hash: string;
	filename: string;
	animated: boolean;
	labels: string[];
}

/** The labels of #126: each image gets one value of each namespace, or
 * one or more of a multi-valued one. */
export const VOCABULARY: Namespace[] = [
	{
		name: 'medium',
		multiple: false,
		values: ['photographic', 'rendered-3d', 'traditional-painted', 'ink-line', '2d-line-fill', 'flat-vector', 'pixel-voxel']
	},
	{
		name: 'style',
		multiple: false,
		values: ['naturalistic', 'semi-stylized', 'cel-shaded', 'stylized', 'flattened']
	},
	{
		name: 'overlay',
		multiple: true,
		values: [
			'none',
			'cinematic',
			'anime-manga',
			'western-comic',
			'cartoon',
			'ukiyo-e',
			'cyberpunk',
			'fantasy',
			'analog-film',
			'retro-8bit'
		]
	},
	{ name: 'rating', multiple: false, values: ['sfw', 'suggestive', 'erotic', 'porn'] },
	{ name: 'age', multiple: true, values: ['none', 'child', 'teen', 'indeterminate', 'adult', 'senior'] }
];

/** Every label the vocabulary can apply, for asking the API. */
export function vocabularyLabels(vocabulary: Namespace[]): string[] {
	return vocabulary.flatMap((ns) => ns.values.map((value) => `${ns.name}:${value}`));
}

function namespaceOf(label: string): string {
	return label.slice(0, label.indexOf(':'));
}

function valueOf(label: string): string {
	return label.slice(label.indexOf(':') + 1);
}

/** The namespace `label` belongs to, if it is one of the vocabulary's own
 * values. A tag sharing only the prefix (a star rating's `rating:3`, next to
 * the vocabulary's `rating:sfw`) is not a label of that namespace. */
function vocabularyLabel(vocabulary: Namespace[], label: string): Namespace | undefined {
	const ns = vocabulary.find((n) => n.name === namespaceOf(label));
	return ns && ns.values.includes(valueOf(label)) ? ns : undefined;
}

/** The tags to add and remove when `label` is clicked on an image. */
export function toggleLabel(
	vocabulary: Namespace[],
	current: string[],
	label: string
): { add: string[]; remove: string[] } {
	if (current.includes(label)) return { add: [], remove: [label] };
	const ns = vocabularyLabel(vocabulary, label);
	const sameNamespace = ns
		? current.filter((l) => vocabularyLabel(vocabulary, l)?.name === ns.name)
		: [];
	if (!ns || !ns.multiple) return { add: [label], remove: sameNamespace };
	const none = `${ns.name}:none`;
	return {
		add: [label],
		remove: label === none ? sameNamespace : sameNamespace.filter((l) => l === none)
	};
}

/** The namespaces in which the image has no label yet. */
export function missingNamespaces(vocabulary: Namespace[], labels: string[]): string[] {
	const present = new Set(
		labels.filter((l) => vocabularyLabel(vocabulary, l) !== undefined).map(namespaceOf)
	);
	return vocabulary.map((n) => n.name).filter((n) => !present.has(n));
}

/** How many images carry each label. */
export function labelCounts(images: ImageLabels[]): Map<string, number> {
	const counts = new Map<string, number>();
	for (const image of images) {
		for (const label of image.labels) counts.set(label, (counts.get(label) ?? 0) + 1);
	}
	return counts;
}

/** The index of the next image after `from` missing a namespace, wrapping
 * round to the start; -1 when every image is labelled. */
export function nextUnlabelled(vocabulary: Namespace[], images: ImageLabels[], from: number): number {
	for (let step = 1; step <= images.length; step++) {
		const i = (from + step) % images.length;
		if (missingNamespaces(vocabulary, images[i].labels).length > 0) return i;
	}
	return -1;
}
