import type { Source } from './types';

/** The sources files can move to: ones Thalimage may change, other than the
 * source they leave. */
export function movableTargets(sources: Source[], fromId: number): Source[] {
	return sources.filter((source) => source.writable && source.id !== fromId);
}

/** A source's name in a choice or a confirmation: its label, else its folder. */
export function sourceName(source: Source): string {
	return source.label || source.path;
}
