// supabase/functions/stripe-cancel-subscription/index.js
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { Stripe } from 'https://esm.sh/stripe@11.1.0'

const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY'))
const supabaseUrl = Deno.env.get('SUPABASE_URL')
const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')

serve(async (req) => {
  try {
    const { subscription_id } = await req.json()
    
    if (!subscription_id) {
      return new Response(JSON.stringify({ error: 'Subscription ID is required' }), { 
        status: 400,
        headers: { 'Content-Type': 'application/json' } 
      })
    }
    
    // Anuluj subskrypcję w Stripe
    // Ustawiamy cancel_at_period_end na true, aby subskrypcja została anulowana na koniec okresu rozliczeniowego
    const subscription = await stripe.subscriptions.update(
      subscription_id,
      { cancel_at_period_end: true }
    )
    
    return new Response(JSON.stringify({ 
      success: true,
      subscription: subscription
    }), { 
      status: 200,
      headers: { 'Content-Type': 'application/json' } 
    })
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), { 
      status: 500,
      headers: { 'Content-Type': 'application/json' } 
    })
  }
})