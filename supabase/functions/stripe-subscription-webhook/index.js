// supabase/functions/stripe-subscription-webhook/index.js
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { Stripe } from 'https://esm.sh/stripe@11.1.0'

const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY'))
const endpointSecret = Deno.env.get('STRIPE_SUBSCRIPTION_WEBHOOK_SECRET')
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
    
    // Obsługa różnych zdarzeń Stripe związanych z subskrypcjami
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object
        
        // Jeśli to subskrypcja
        if (session.mode === 'subscription') {
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
          
          // Dodaj kredyty użytkownikowi za pierwszą płatność
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
              transaction_type: 'subscription',
              amount: credits,
              credits_before: currentCredits,
              credits_after: currentCredits + credits,
              description: `Miesięczna subskrypcja kredytów przez Stripe`
            })
          })
          
          // Zapisz informacje o subskrypcji
          // Pobierz szczegóły subskrypcji
          const subscription = await stripe.subscriptions.retrieve(session.subscription)
          
          // Oblicz datę następnego odnowienia
          const nextBillingDate = new Date(subscription.current_period_end * 1000)
          
          // Zapisz lub aktualizuj subskrypcję
          const paymentMethodResponse = await fetch(`${supabaseUrl}/rest/v1/payment_methods?code=eq.stripe_subscription`, {
            headers: {
              'Content-Type': 'application/json',
              'apikey': supabaseKey,
              'Authorization': `Bearer ${supabaseKey}`
            }
          })
          
          const paymentMethods = await paymentMethodResponse.json()
          const paymentMethodId = paymentMethods[0].id
          
          await fetch(`${supabaseUrl}/rest/v1/subscriptions`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'apikey': supabaseKey,
              'Authorization': `Bearer ${supabaseKey}`
            },
            body: JSON.stringify({
              user_id: userId,
              payment_method_id: paymentMethodId,
              credit_package_id: packageId,
              status: 'active',
              next_billing_date: nextBillingDate.toISOString(),
              external_subscription_id: subscription.id,
              subscription_data: subscription
            })
          })
        }
        break
      }
      
      case 'invoice.payment_succeeded': {
        const invoice = event.data.object
        
        // Pobierz szczegóły subskrypcji
        const subscription = await stripe.subscriptions.retrieve(invoice.subscription)
        const userId = parseInt(subscription.metadata.user_id || '0')
        
        // Jeśli to nie pierwsza opłata (pierwszą obsługujemy w checkout.session.completed)
        if (invoice.billing_reason === 'subscription_cycle') {
          // Pobierz dane subskrypcji z bazy
          const subResponse = await fetch(`${supabaseUrl}/rest/v1/subscriptions?external_subscription_id=eq.${invoice.subscription}`, {
            headers: {
              'Content-Type': 'application/json',
              'apikey': supabaseKey,
              'Authorization': `Bearer ${supabaseKey}`
            }
          })
          
          const subs = await subResponse.json()
          if (subs.length === 0) {
            throw new Error(`Subscription not found: ${invoice.subscription}`)
          }
          
          const sub = subs[0]
          const packageId = sub.credit_package_id
          
          // Pobierz dane pakietu
          const packageResponse = await fetch(`${supabaseUrl}/rest/v1/credit_packages?id=eq.${packageId}`, {
            headers: {
              'Content-Type': 'application/json',
              'apikey': supabaseKey,
              'Authorization': `Bearer ${supabaseKey}`
            }
          })
          
          const packages = await packageResponse.json()
          if (packages.length === 0) {
            throw new Error(`Package not found: ${packageId}`)
          }
          
          const packageData = packages[0]
          const credits = packageData.credits
          
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
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'apikey': supabaseKey,
              'Authorization': `Bearer ${supabaseKey}`
            },
            body: JSON.stringify({
              credits_amount: currentCredits + credits,
              total_credits_purchased: userCredits[0].total_credits_purchased + credits,
              last_purchase_date: new Date().toISOString(),
              total_spent: parseFloat(userCredits[0].total_spent) + parseFloat(invoice.amount_paid / 100)
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
              transaction_type: 'subscription_renewal',
              amount: credits,
              credits_before: currentCredits,
              credits_after: currentCredits + credits,
              description: `Odnowienie miesięcznej subskrypcji kredytów`
            })
          })
          
          // Aktualizuj datę następnego odnowienia
          const nextBillingDate = new Date(subscription.current_period_end * 1000)
          
          await fetch(`${supabaseUrl}/rest/v1/subscriptions?id=eq.${sub.id}`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'apikey': supabaseKey,
              'Authorization': `Bearer ${supabaseKey}`
            },
            body: JSON.stringify({
              next_billing_date: nextBillingDate.toISOString(),
              updated_at: new Date().toISOString(),
              subscription_data: subscription
            })
          })
        }
        break
      }
      
      case 'customer.subscription.deleted': {
        const subscription = event.data.object
        
        // Zaktualizuj status subskrypcji
        await fetch(`${supabaseUrl}/rest/v1/subscriptions?external_subscription_id=eq.${subscription.id}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'apikey': supabaseKey,
            'Authorization': `Bearer ${supabaseKey}`
          },
          body: JSON.stringify({
            status: 'cancelled',
            end_date: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            subscription_data: subscription
          })
        })
        break
      }
      
      case 'customer.subscription.updated': {
        const subscription = event.data.object
        
        // Zaktualizuj status subskrypcji
        const status = subscription.status === 'active' ? 'active' : 
                      subscription.status === 'paused' ? 'paused' : 
                      subscription.status === 'canceled' ? 'cancelled' : 
                      subscription.status
        
        await fetch(`${supabaseUrl}/rest/v1/subscriptions?external_subscription_id=eq.${subscription.id}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'apikey': supabaseKey,
            'Authorization': `Bearer ${supabaseKey}`
          },
          body: JSON.stringify({
            status: status,
            updated_at: new Date().toISOString(),
            subscription_data: subscription
          })
        })
        break
      }
    }
    
    return new Response(JSON.stringify({ received: true }), { 
      status: 200,
      headers: { 'Content-Type': 'application/json' } 
    })
  } catch (error) {
    console.error('Error processing webhook:', error)
    return new Response(JSON.stringify({ error: error.message }), { 
      status: 500,
      headers: { 'Content-Type': 'application/json' } 
    })
  }
})