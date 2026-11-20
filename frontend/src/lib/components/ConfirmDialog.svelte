<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * A modal asking to confirm an action. Cancel has the focus, so Enter or
	 * Escape never confirms by accident; `danger` styles the confirm button
	 * for actions that cannot be undone. With `canConfirm` false the dialog
	 * only explains why the action is not possible. While `busy`, the action
	 * is under way: both buttons wait, so it cannot be started twice, and the
	 * confirm button says so.
	 */
	let {
		open,
		title,
		confirmLabel,
		busyLabel = 'Working…',
		danger = false,
		canConfirm = true,
		busy = false,
		onconfirm,
		oncancel,
		children
	}: {
		open: boolean;
		title: string;
		confirmLabel: string;
		busyLabel?: string;
		danger?: boolean;
		canConfirm?: boolean;
		busy?: boolean;
		onconfirm: () => void;
		oncancel: () => void;
		children: Snippet;
	} = $props();

	let dialog: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (!dialog) return;
		if (open && !dialog.open) dialog.showModal();
		if (!open && dialog.open) dialog.close();
	});

	/** Escape asks to cancel; while the action runs it leaves the dialog up,
	 * since the request cannot be withdrawn. */
	function onNativeCancel(event: Event) {
		event.preventDefault();
		if (!busy) oncancel();
	}
</script>

<dialog bind:this={dialog} oncancel={onNativeCancel} aria-labelledby="confirm-title">
	<h3 id="confirm-title">{title}</h3>
	<div class="body" aria-busy={busy}>{@render children()}</div>
	<div class="actions">
		<!-- svelte-ignore a11y_autofocus -->
		<button class="control" autofocus onclick={oncancel} disabled={busy}>Cancel</button>
		{#if canConfirm}
			<button
				class="control {danger ? 'control-danger' : 'control-primary'}"
				onclick={onconfirm}
				disabled={busy}
			>
				{busy ? busyLabel : confirmLabel}
			</button>
		{/if}
	</div>
</dialog>

<style>
	dialog {
		max-width: min(560px, calc(100vw - 32px));
		padding: 20px;
		border: 1px solid #444;
		border-radius: 6px;
		background: #1e1e1e;
		color: #ddd;
	}

	dialog::backdrop {
		background: rgba(0, 0, 0, 0.6);
	}

	h3 {
		margin: 0 0 12px;
	}

	.body {
		font-size: 0.9rem;
		max-height: 50vh;
		overflow-y: auto;
		overflow-wrap: anywhere;
	}

	.actions {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		margin-top: 16px;
	}
</style>
