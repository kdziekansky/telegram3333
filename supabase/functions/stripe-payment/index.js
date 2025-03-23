// supabase/functions/stripe-payment/index.js
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { Stripe } from 'https://esm.sh/stripe@11.1.0'

const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY'))
const supabaseUrl = Deno.env.get('SUPABASE_URL')
const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')

serve(async (req) => {
  try {
    const { user_id, package_id, success_url, cancel_url } = await req.json()
    
    // Pobierz dane pakietu z bazy
    const packageResponse = await fetch(`${supabaseUrl}/rest/v1/credit_packages?id=eq.${package_id}`, {
      headers: {
        'Content-Type': 'application/json',
        'apikey': supabaseKey,
        'Authorization': `Bearer ${supabaseKey}`
      }
    })
    
    const packages = await packageResponse.json()
    if (packages.length === 0) {
      return new Response(JSON.stringify({ error: 'Package not found' }), { 
        status: 400,
        headers: { 'Content-Type': 'application/json' } 
      })
    }
    
    const packageData = packages[0]
    
    // Utwórz sesję płatności Stripe
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card', 'blik', 'p24'],
      line_items: [
        {
          price_data: {
            currency: 'pln',
            product_data: {
              name: packageData.name,
              description: `${packageData.credits} credits`
            },
            unit_amount: Math.round(packageData.price * 100),
          },
          quantity: 1,
        },
      ],
      mode: 'payment',
      success_url: success_url,
      cancel_url: cancel_url,
      client_reference_id: user_id.toString(),
      metadata: {
        user_id: user_id.toString(),
        package_id: package_id.toString(),
        credits: packageData.credits.toString()
      }
    })
    
    // Zapisz informacje o transakcji w bazie
    const paymentMethodResponse = await fetch(`${supabaseUrl}/rest/v1/payment_methods?code=eq.stripe`, {
      headers: {
        'Content-Type': 'application/json',
        'apikey': supabaseKey,
        'Authorization': `Bearer ${supabaseKey}`
      }
    })
    
    const paymentMethods = await paymentMethodResponse.json()
    const paymentMethodId = paymentMethods[0].id
    
    const transaction = {
      user_id: user_id,
      payment_method_id: paymentMethodId,
      credit_package_id: package_id,
      amount: packageData.price,
      currency: 'PLN',
      status: 'pending',
      external_transaction_id: session.id,
      payment_data: { session_id: session.id }
    }
    
    await fetch(`${supabaseUrl}/rest/v1/payment_transactions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': supabaseKey,
        'Authorization': `Bearer ${supabaseKey}`
      },
      body: JSON.stringify(transaction)
    })
    
    return new Response(JSON.stringify({ url: session.url }), { 
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