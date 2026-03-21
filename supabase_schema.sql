-- 1. Create the Profiles Table
create table public.profiles (
  id uuid references auth.users not null primary key,
  username text unique,
  role text default 'citizen' check (role in ('citizen', 'admin')),
  age integer default 30,
  has_asthma boolean default false,
  home_ward text
);

-- 2. Turn on Row Level Security (RLS)
alter table public.profiles enable row level security;

-- 3. Policy: Users can view their own profile or Admins can view all
create policy "Users can view own profile" 
on profiles for select 
using ( auth.uid() = id );

create policy "Admins can view all profiles" 
on profiles for select 
using ( exists (select 1 from profiles where id = auth.uid() and role = 'admin') );

-- 4. Policy: Users can update their own profile
create policy "Users can update own profile" 
on profiles for update 
using ( auth.uid() = id );

-- 5. Trigger: Automatically generate a profile when a user signs up on the frontend
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, username, role, home_ward)
  -- Default to 'citizen'. Set to 'admin' manually in dashboard for the Mayor
  values (new.id, new.email, 'citizen', 'Punjabi Bagh'); 
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
