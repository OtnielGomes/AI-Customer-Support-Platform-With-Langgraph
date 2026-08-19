"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { CONSOLE_COOKIE, consoleSessionToken, requireConsoleAuth, tokensMatch } from "@/lib/auth";
import { closeTicket, replyToEscalation, takeoverTicket } from "@/lib/api/server";

export async function loginAction(formData: FormData): Promise<{ error: string } | void> {
  const password = String(formData.get("password") ?? "");
  const nextPath = String(formData.get("next") ?? "/console/inbox");
  const expected = process.env.CONSOLE_PASSWORD ?? "";
  if (!expected || !tokensMatch(password, expected)) {
    return { error: "Invalid password" };
  }
  const jar = await cookies();
  jar.set(CONSOLE_COOKIE, consoleSessionToken(), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  redirect(nextPath.startsWith("/") ? nextPath : "/console/inbox");
}

export async function logoutAction(): Promise<void> {
  const jar = await cookies();
  jar.delete(CONSOLE_COOKIE);
  redirect("/login");
}

export async function replyEscalationAction(
  ticketId: string,
  formData: FormData,
): Promise<void> {
  await requireConsoleAuth();
  const answer = String(formData.get("answer") ?? "").trim();
  if (!answer) {
    throw new Error("Answer is required");
  }
  await replyToEscalation(ticketId, answer, "console");
  redirect(`/console/inbox/${ticketId}`);
}

export async function closeTicketAction(
  ticketId: string,
  formData: FormData,
): Promise<{ error: string } | void> {
  await requireConsoleAuth();
  const reason = String(formData.get("reason") ?? "").trim();
  try {
    await closeTicket(ticketId, reason || undefined);
  } catch (caught) {
    return {
      error: caught instanceof Error ? caught.message : "Could not close ticket",
    };
  }
  redirect(`/console/tickets/${ticketId}`);
}

export async function takeoverAction(
  ticketId: string,
): Promise<{ error: string } | void> {
  await requireConsoleAuth();
  try {
    await takeoverTicket(ticketId, "console");
  } catch (caught) {
    return {
      error: caught instanceof Error ? caught.message : "Could not take over",
    };
  }
  revalidatePath(`/console/inbox/${ticketId}`);
}

export async function closeConversationAction(
  ticketId: string,
  formData: FormData,
): Promise<{ error: string } | void> {
  await requireConsoleAuth();
  const reason = String(formData.get("reason") ?? "").trim();
  try {
    await closeTicket(ticketId, reason || undefined);
  } catch (caught) {
    return {
      error: caught instanceof Error ? caught.message : "Could not close ticket",
    };
  }
  revalidatePath("/console/inbox");
  revalidatePath(`/console/inbox/${ticketId}`);
}
