notify pgrst, 'reload schema';

select
  to_regprocedure('public.login_or_register_app_user(text)') as login_rpc,
  has_function_privilege('anon', 'public.login_or_register_app_user(text)', 'execute') as anon_can_execute;
