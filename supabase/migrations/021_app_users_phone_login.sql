create extension if not exists pgcrypto;

create table if not exists public.app_users (
  id uuid primary key default gen_random_uuid(),
  phone text not null unique,
  display_name text not null,
  status text not null default 'active' check (status in ('active', 'disabled')),
  created_at timestamptz not null default now(),
  last_login_at timestamptz not null default now()
);

create index if not exists idx_app_users_phone
  on public.app_users (phone);

alter table public.app_users enable row level security;

drop policy if exists "deny direct app users read" on public.app_users;
drop policy if exists "deny direct app users write" on public.app_users;

create or replace function public.login_or_register_app_user(p_phone text)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_phone text;
  v_user public.app_users;
begin
  v_phone := regexp_replace(coalesce(p_phone, ''), '\s+', '', 'g');

  if v_phone !~ '^1[3-9][0-9]{9}$' then
    raise exception '请输入有效的11位手机号';
  end if;

  insert into public.app_users (phone, display_name, last_login_at)
  values (v_phone, '用户' || right(v_phone, 4), now())
  on conflict (phone) do update set
    last_login_at = now()
  returning * into v_user;

  if v_user.status <> 'active' then
    raise exception '该账号已停用';
  end if;

  return jsonb_build_object(
    'id', v_user.id,
    'phone', v_user.phone,
    'display_name', v_user.display_name,
    'status', v_user.status,
    'created_at', v_user.created_at,
    'last_login_at', v_user.last_login_at
  );
end;
$$;

revoke all on function public.login_or_register_app_user(text) from public;
grant execute on function public.login_or_register_app_user(text) to anon, authenticated;
