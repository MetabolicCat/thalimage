<script lang="ts">
	import { copyPath } from '$lib/imageCopies';
	import { sourceName } from '$lib/sourceTargets';
	import type { ImageCopy, Source } from '$lib/types';
	import ConfirmDialog from './ConfirmDialog.svelte';

	/**
	 * Confirms moving files into another source's folder: lists each file with
	 * the path it takes there, and its sidecars. `message` reports what went
	 * wrong last time.
	 */
	let {
		to,
		copies,
		message,
		onconfirm,
		oncancel
	}: {
		to: Source;
		copies: ImageCopy[];
		message: string;
		onconfirm: () => void;
		oncancel: () => void;
	} = $props();

	const files = $derived(copies.length);
	const one = $derived(files === 1);
	const sidecars = $derived(copies.reduce((n, c) => n + c.sidecars.length, 0));

	/** The path a copy takes in the target source. */
	function destination(copy: ImageCopy): string {
		return copyPath({ ...copy, source_path: to.path });
	}
</script>

<ConfirmDialog
	open
	title={one ? `Move this file to ${sourceName(to)}?` : `Move ${files} files to ${sourceName(to)}?`}
	confirmLabel="Move {files} {one ? 'file' : 'files'}"
	canConfirm={files > 0}
	{onconfirm}
	{oncancel}
>
	{#if message}
		<p class="confirm-message">{message}</p>
	{/if}
	<p>
		Each file keeps its path under the target's folder, and stays the same image there: its
		tags, scores, votes and collections are kept. A name the target already uses sends the file to
		its picture hash instead.
	</p>
	<ul class="file-list">
		{#each copies as copy (copy.relative_path)}
			<li>
				{destination(copy)}
				{#each copy.sidecars as sidecar (sidecar)}
					<div class="file-note">+ {destination({ ...copy, relative_path: sidecar })}</div>
				{/each}
			</li>
		{/each}
	</ul>
	{#if sidecars > 0}
		<p>{sidecars} sidecar {sidecars === 1 ? 'file goes' : 'files go'} along with {one ? 'it' : 'them'}.</p>
	{/if}
</ConfirmDialog>

<style>
	.confirm-message {
		color: #f88;
	}

	.file-note {
		color: #888;
	}

	.file-list {
		margin: 8px 0;
		padding-left: 18px;
		font-family: monospace;
		font-size: 0.8rem;
	}
</style>
