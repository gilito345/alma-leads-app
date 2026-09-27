"use server";

import { revalidatePath } from "next/cache";

import { ApiError, updateLeadState } from "@/lib/api";

export interface MarkState {
  error: string | null;
}

export async function markReachedOutAction(leadId: string, _: MarkState): Promise<MarkState> {
  try {
    await updateLeadState(leadId, "REACHED_OUT");
  } catch (error) {
    // redirect() (e.g. on an expired session) signals by throwing; let it through.
    if (!(error instanceof ApiError)) throw error;
    return { error: error.status === 404 ? "This lead no longer exists." : error.message };
  }
  revalidatePath("/leads");
  revalidatePath(`/leads/${leadId}`);
  return { error: null };
}
