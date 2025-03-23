// supabase/functions/stripe-webhook/index.js
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { Stripe } from 'https://esm.sh/stripe@11.1.0'

const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY'))
const endpointSecret = Deno.env.get('STRIPE_WEBHOOK_SECRET')
const supabaseUrl = Deno.env.get('SUPABASE_URL')
const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')

serve(async (req) => {
  try {
    const signature = req.headers.get('stripe-signature')
    const body = await req.text()
    
    let event
    try {
      event = stripe.webhooks.constructEvent(body, signature, endpointSecret)
    } catch (err) {
      return new Response(JSON.stringify({ error: `Webhook signature verification failed: ${err.message}` }), { 
        status: 400,
        headers: { 'Content-Type': 'application/json' } 
      })
    }
    
    // Obsługa różnych zdarzeń Stripe
    if (event.type === 'checkout.session.completed') {
      const session = event.data.object
      
      // Aktualizuj status transakcji
      await fetch(`${supabaseUrl}/rest/v1/payment_transactions?external_transaction_id=eq.${session.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'apikey': supabaseKey,
          'Authorization': `Bearer ${supabaseKey}`
        },
        body: JSON.stringify({
          status: 'completed',
          updated_at: new Date().toISOString()
        })
      })
      
      // Dodaj kredyty użytkownikowi
      const userId = parseInt(session.metadata.user_id)
      const packageId = parseInt(session.metadata.package_id)
      const credits = parseInt(session.metadata.credits)
      
      // Pobierz aktualną liczbę kredytów
      const creditResponse = await fetch(`${supabaseUrl}/rest/v1/user_credits?user_id=eq.${userId}`, {
        headers: {
          'Content-Type': 'application/json',
          'apikey': supabaseKey,
          'Authorization': `Bearer ${supabaseKey}`
        }
      })
      
      const userCredits = await creditResponse.json()
      const currentCredits = userCredits.length > 0 ? userCredits[0].credits_amount : 0
      
      // Aktualizuj kredyty użytkownika
      await fetch(`${supabaseUrl}/rest/v1/user_credits?user_id=eq.${userId}`, {
        method: userCredits.length > 0 ? 'PATCH' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': supabaseKey,
          'Authorization': `Bearer ${supabaseKey}`
        },
        body: JSON.stringify({
          user_id: userId,
          credits_amount: currentCredits + credits,
          total_credits_purchased: userCredits.length > 0 ? 
            userCredits[0].total_credits_purchased + credits : credits,
          last_purchase_date: new Date().toISOString(),
          total_spent: userCredits.length > 0 ? 
            parseFloat(userCredits[0].total_spent) + parseFloat(session.amount_total / 100) : 
            parseFloat(session.amount_total / 100)
        })
      })
      
      // Dodaj transakcję kredytową
      await fetch(`${supabaseUrl}/rest/v1/credit_transactions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': supabaseKey,
          'Authorization': `Bearer ${supabaseKey}`
        },
        body: JSON.stringify({
          user_id: userId,
          transaction_type: 'purchase',
          amount: credits,
          credits_before: currentCredits,
          credits_after: currentCredits + credits,
          description: `Zakup pakietu kredytów przez Stripe`
        })
      })
    }
    
    return new Response(JSON.stringify({ received: true }), { 
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