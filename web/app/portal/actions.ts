"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { PORTAL_COOKIE, portalSessionToken } from "@/lib/auth";
import { validatePortalSession } from "@/lib/api/server";

export async function portalLoginAction(
  formData: FormData,
): Promise<{ error: string } | void> {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  if (!email) {
    return { error: "Informe o e-mail da sua conta TechStore." };
  }
  try {
    await validatePortalSession(email);
  } catch (caught) {
    return {
      error:
        caught instanceof Error
          ? caught.message
          : "Não encontramos uma conta com esse e-mail.",
    };
  }
  const jar = await cookies();
  jar.set(PORTAL_COOKIE, portalSessionToken(email), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  redirect("/");
}

export async function portalLogoutAction(): Promise<void> {
  const jar = await cookies();
  jar.delete(PORTAL_COOKIE);
  redirect("/portal/login");
}
