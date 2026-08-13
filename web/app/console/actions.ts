"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { CONSOLE_COOKIE, consoleSessionToken, requireConsoleAuth } from "@/lib/auth";
import { closeTicket, replyToEscalation } from "@/lib/api/server";

export async function loginAction(formData: FormData): Promise<{ error: string } | void> {
  const password = String(formData.get("password") ?? "");
  const nextPath = String(formData.get("next") ?? "/console/tickets");
  if (password !== process.env.CONSOLE_PASSWORD) {
    return { error: "Invalid password" };
  }
  const jar = await cookies();
  jar.set(CONSOLE_COOKIE, consoleSessionToken(), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  redirect(nextPath.startsWith("/") ? nextPath : "/console/tickets");
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
  redirect(`/console/tickets/${ticketId}`);
}

export async function closeTicketAction(
  ticketId: string,
  formData: FormData,
): Promise<void> {
  await requireConsoleAuth();
  const reason = String(formData.get("reason") ?? "").trim();
  await closeTicket(ticketId, reason || undefined);
  redirect(`/console/tickets/${ticketId}`);
}
