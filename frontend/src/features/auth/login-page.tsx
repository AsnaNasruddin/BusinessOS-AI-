import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { BrandMark } from '@/components/layout/icons'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

type LoginForm = z.infer<typeof loginSchema>

export function LoginPage() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  // TODO(learning): wire to `api.post('/auth/login', data)` once Module 1 (Auth) has a backend.
  async function onSubmit(data: LoginForm) {
    await new Promise((resolve) => setTimeout(resolve, 400))
    console.info('login submitted', data)
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

          <Button type="submit" variant="primary" disabled={isSubmitting} className="mt-1 w-full">
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </Card>
    </div>
  )
}
