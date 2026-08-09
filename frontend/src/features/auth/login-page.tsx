import { zodResolver } from '@hookform/resolvers/zod'
import { isAxiosError } from 'axios'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { BrandMark } from '@/components/layout/icons'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { api, fetchProfile } from '@/lib/api'
import { useAuthStore } from '@/stores/auth-store'

const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

type LoginForm = z.infer<typeof loginSchema>

export function LoginPage() {
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  async function onSubmit(data: LoginForm) {
    setFormError(null)
    try {
      const { data: tokens } = await api.post('/auth/login', data)
      useAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token)

      const { user, memberships } = await fetchProfile()
      useAuthStore.getState().setProfile(user, memberships)

      navigate('/dashboard', { replace: true })
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 401) {
        setFormError('Incorrect email or password.')
      } else {
        setFormError('Something went wrong — please try again.')
      }
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-bg px-4">
      <Card className="w-full max-w-sm p-7">
        <div className="mb-6 flex items-center gap-2.5">
          <BrandMark />
          <span className="text-base font-semibold tracking-tight">BusinessOS</span>
        </div>

        <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
          <div>
            <label htmlFor="email" className="mb-1.5 block text-[12.5px] font-medium text-fg-dim">
              Email
            </label>
            <Input id="email" type="email" placeholder="demo@businessos.ai" {...register('email')} />
            {errors.email && <p className="mt-1 text-xs text-critical-text">{errors.email.message}</p>}
          </div>

          <div>
            <label htmlFor="password" className="mb-1.5 block text-[12.5px] font-medium text-fg-dim">
              Password
            </label>
            <Input id="password" type="password" placeholder="••••••••" {...register('password')} />
            {errors.password && (
              <p className="mt-1 text-xs text-critical-text">{errors.password.message}</p>
            )}
          </div>

          {formError && <p className="text-xs text-critical-text">{formError}</p>}

          <Button type="submit" variant="primary" disabled={isSubmitting} className="mt-1 w-full">
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>

        <p className="mt-5 text-center text-[12.5px] text-fg-dim">
          New to BusinessOS?{' '}
          <Link to="/register" className="font-medium text-signal-ink hover:underline">
            Create an account
          </Link>
        </p>
      </Card>
    </div>
  )
}
