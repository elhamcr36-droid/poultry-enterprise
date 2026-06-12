import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function jsonResponse(body: Record<string, unknown>, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function normalizePhone(phone: string) {
  return String(phone || "").replace(/\D/g, "");
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return jsonResponse({ ok: false, error: "Method not allowed" }, 405);
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

  if (!supabaseUrl || !serviceRoleKey) {
    return jsonResponse({ ok: false, error: "Server is not configured for password reset" }, 500);
  }

  const supabaseAdmin = createClient(supabaseUrl, serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });

  let payload: { email?: string; phone?: string; new_password?: string };
  try {
    payload = await req.json();
  } catch (_error) {
    return jsonResponse({ ok: false, error: "Invalid request body" }, 400);
  }

  const email = String(payload.email || "").trim().toLowerCase();
  const phone = normalizePhone(String(payload.phone || ""));
  const newPassword = String(payload.new_password || "");

  if (!email || !phone || !newPassword) {
    return jsonResponse({ ok: false, error: "กรุณากรอกอีเมล เบอร์โทร และรหัสผ่านใหม่ให้ครบ" }, 400);
  }

  if (newPassword.length < 8) {
    return jsonResponse({ ok: false, error: "รหัสผ่านใหม่ต้องยาวอย่างน้อย 8 ตัวอักษร" }, 400);
  }

  let matchedUser: any = null;
  for (let page = 1; page <= 20 && !matchedUser; page += 1) {
    const { data, error } = await supabaseAdmin.auth.admin.listUsers({ page, perPage: 1000 });
    if (error) {
      return jsonResponse({ ok: false, error: error.message }, 500);
    }

    matchedUser = data.users.find((user) => String(user.email || "").toLowerCase() === email);
    if (!data.users.length || data.users.length < 1000) {
      break;
    }
  }

  if (!matchedUser) {
    return jsonResponse({ ok: false, error: "ไม่พบบัญชีผู้ใช้นี้ในระบบ" }, 404);
  }

  const metadataPhone = normalizePhone(
    matchedUser.user_metadata?.phone ||
      matchedUser.user_metadata?.tel ||
      matchedUser.phone ||
      "",
  );

  if (!metadataPhone || metadataPhone !== phone) {
    return jsonResponse({ ok: false, error: "อีเมลหรือเบอร์โทรไม่ตรงกับข้อมูลที่ลงทะเบียนไว้" }, 403);
  }

  const { error: updateError } = await supabaseAdmin.auth.admin.updateUserById(matchedUser.id, {
    password: newPassword,
  });

  if (updateError) {
    return jsonResponse({ ok: false, error: updateError.message }, 500);
  }

  return jsonResponse({ ok: true });
});
