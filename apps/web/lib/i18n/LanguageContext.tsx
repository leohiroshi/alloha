"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

type Language = "en" | "pt-BR";

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

// Translations
const translations: Record<Language, Record<string, string>> = {
  en: {
    // Navigation
    "nav.about": "About",
    "nav.blog": "Blog",
    "nav.features": "Features",
    "nav.pricing": "Pricing",
    "nav.faq": "FAQ",
    "nav.bookCall": "Start free trial",

    // Hero
    "hero.urgency": "Hurry, only",
    "hero.spotsLeft": "5 spots left.",
    "hero.title1": "The truly ",
    "hero.titleHighlight": "Limitless",
    "hero.title2": "AI assistant.",
    "hero.subtitle1": "Say goodbye to missed leads, and hello to",
    "hero.subtitleHighlight": "limitless",
    "hero.subtitle2": ", lightning fast responses.",
    "hero.ctaPrimary": "Get started free",
    "hero.ctaSecondary": "Sign in to configure",
    "hero.socialProof": "Our clients are featured on",

    // Phone Chat
    "phone.online": "Online 24/7",
    "phone.chat1": "Looking for a 2 bedroom in Miami Beach",
    "phone.chat2": "Found 12 perfect options! 🏠",
    "phone.chat3": "Want to schedule visits for tomorrow?",
    "phone.chat4": "Yes! 2 PM would be perfect 👍",
    "phone.placeholder": "Type a message...",

    // Wave Chat Bubble
    "bubble.online": "Alloha AI • Online",
    "bubble.message": "Found 3 perfect apartments downtown. Want me to schedule visits?",

    // Stats
    "stats.thisWeek": "This week",
    "stats.leads": "+234 leads",
    "stats.vsLastWeek": "vs last week",

    // Testimonials
    "testimonial1.quote": "Alloha delivers beautiful, highly-converting leads in record time. It's hard to find a better solution and Alloha has earned it. Look forward to working in the future.",
    "testimonial1.author": "Tony Soprano",
    "testimonial1.role": "CEO at ReMax",
    "testimonial2.quote": "Getting design done was such a pain. I am so glad we found Alloha. The AI is incredible, the work is refreshingly painless.",
    "testimonial2.author": "Jenny Larkspur",
    "testimonial2.role": "Real Estate Agent",
    "testimonial3.quote": "The 24/7 availability has been a game changer. We never miss a lead anymore, even at 3 AM. Our conversion rate has doubled.",
    "testimonial3.author": "Marcus Chen",
    "testimonial3.role": "Broker at Keller Williams",

    // Process
    "process.label": "Process",
    "process.title": "Your leads,",
    "process.titleHighlight": "effortlessly.",
    "process.subtitle": "Begin your AI journey in three effortless steps.",
    "process.step1.title": "Subscribe",
    "process.step1.desc": "Subscribe to a plan & request as many designs as you'd like.",
    "process.step2.title": "Receive",
    "process.step2.desc": "Receive your design as fast as two business days on average.",
    "process.step3.title": "Revise",
    "process.step3.desc": "We'll revise the designs until you're 100% satisfied.",
    "process.cta": "Start 7-day free trial",

    // Bento Grid
    "bento.visualize.title": "Visualize your leads",
    "bento.visualize.desc": "See all conversations in one dashboard",
    "bento.brand.title": "Find your leads, own your brand",
    "bento.brand.desc": "Customizable AI that speaks your voice",
    "bento.multiplatform.title": "Multiplatform Collaboration",
    "bento.multiplatform.desc": "Connect with WhatsApp, Instagram, Website",
    "bento.mockups.title": "E-Mockups Available",
    "bento.mockups.desc": "Generate property presentations instantly",
    "bento.internet.title": "The Internet is your canvas",
    "bento.internet.desc": "Capture leads from any source",

    // Benefits
    "benefits.label": "Benefits",
    "benefits.title": "Fast, quality",
    "benefits.titleHighlight": "& limitless.",
    "benefits.subtitle": "Alloha replaces unreliable manual responses with AI-powered conversations, delivered so fast that it will blow your mind.",
    "benefits.item1.title": "Submit Unlimited Requests",
    "benefits.item1.desc": "Submit as many requests as you like and we'll get to work on them, one by one.",
    "benefits.item2.title": "Manage with Dashboard",
    "benefits.item2.desc": "Manage your conversations using Dashboard. View active, queued and completed tasks with ease.",
    "benefits.item3.title": "Pause Anytime",
    "benefits.item3.desc": "No more contracts! Just hit pause and resume your subscription at a future date.",
    "benefits.testimonial": "\"Getting design done was such a pain. I am so glad we found Alloha. The work is incredibly refreshingly painless.\"",
    "benefits.testimonial.author": "Jenny Larkspur",
    "benefits.testimonial.role": "Real Estate Agent",

    // Features
    "features.label": "Features",
    "features.title": "Reasons you will",
    "features.titleHighlight": "love us.",
    "features.subtitle": "Once you try Alloha, you'll never go anywhere else for AI. Seriously.",
    "features.designBoard.title": "Design Board",
    "features.designBoard.desc": "Request as many designs as you like on your own design board.",
    "features.delivery.title": "Lightning Fast Delivery",
    "features.delivery.desc": "Receive your designs as fast as 1-2 business days.",
    "features.rate.title": "Fixed Monthly Rate",
    "features.rate.desc": "No surprises. Pay the same fixed price every month.",
    "features.designs.title": "Award-Winning Designs",
    "features.designs.desc": "Leave your customers in awe with award-winning designs.",
    "features.revisions.title": "Unlimited Revisions",
    "features.revisions.desc": "Revise your designs until you're 100% satisfied. No limits.",
    "features.unique.title": "Unique & All Yours",
    "features.unique.desc": "All your designs are crafted especially for you.",
    "features.cta": "Start 7-day free trial",

    // Solutions
    "solutions.label": "Solutions",
    "solutions.title": "All your",
    "solutions.titleHighlight": "needs",
    "solutions.title2": "covered.",
    "solutions.subtitle": "Running a successful business means more than just a website. That's why we cover all your real estate needs.",
    "solutions.logos": "Logos",
    "solutions.landingPages": "Landing Pages",
    "solutions.websites": "Websites",
    "solutions.digitalProducts": "Digital Products",
    "solutions.pitchDecks": "Pitch Decks",
    "solutions.mobileApps": "Mobile Apps",
    "solutions.emailDesign": "Email Design",
    "solutions.productDesign": "Product Design",

    // Pricing
    "pricing.label": "Pricing",
    "pricing.title": "Pricing that's so",
    "pricing.titleHighlight": "simple.",
    "pricing.subtitle": "Choose the plan that fits your business. No hidden fees, no surprises.",
    "pricing.mostPopular": "MOST POPULAR",
    "pricing.starter.name": "Starter",
    "pricing.starter.price": "$97",
    "pricing.starter.period": "/month",
    "pricing.starter.desc": "Perfect for individual agents",
    "pricing.starter.feature1": "1 WhatsApp number",
    "pricing.starter.feature2": "500 conversations/month",
    "pricing.starter.feature3": "Basic dashboard",
    "pricing.starter.feature4": "Email support",
    "pricing.starter.feature5": "Responses in up to 5 seconds",
    "pricing.starter.cta": "Get started",
    "pricing.pro.name": "Professional",
    "pricing.pro.price": "$197",
    "pricing.pro.period": "/month",
    "pricing.pro.desc": "Ideal for growing agencies",
    "pricing.pro.feature1": "5 WhatsApp numbers",
    "pricing.pro.feature2": "Unlimited conversations",
    "pricing.pro.feature3": "Advanced dashboard",
    "pricing.pro.feature4": "Priority support",
    "pricing.pro.feature5": "CRM integration",
    "pricing.pro.feature6": "Custom reports",
    "pricing.pro.feature7": "Custom AI training",
    "pricing.pro.cta": "Get started",
    "pricing.enterprise.name": "Enterprise",
    "pricing.enterprise.price": "Custom",
    "pricing.enterprise.period": "",
    "pricing.enterprise.desc": "For large operations",
    "pricing.enterprise.feature1": "Unlimited WhatsApp",
    "pricing.enterprise.feature2": "Dedicated API",
    "pricing.enterprise.feature3": "Account manager",
    "pricing.enterprise.feature4": "Guaranteed SLA",
    "pricing.enterprise.feature5": "Custom onboarding",
    "pricing.enterprise.feature6": "Custom integrations",
    "pricing.enterprise.cta": "Contact sales",
    "pricing.trial": "7-day free trial",

    // FAQ
    "faq.label": "FAQ",
    "faq.title": "Frequently asked",
    "faq.titleHighlight": "questions.",
    "faq.subtitle": "Everything you need to know about Alloha.",
    "faq.q1": "How does Alloha work?",
    "faq.a1": "Alloha is an AI assistant that automatically responds to your leads' messages on WhatsApp, Instagram, and your website. It qualifies leads, schedules visits, and transfers important conversations to you.",
    "faq.q2": "Can I customize the AI responses?",
    "faq.a2": "Yes! You can train the AI with information about your properties, prices, locations, and your brand's tone of voice. The AI learns and improves continuously.",
    "faq.q3": "How long does setup take?",
    "faq.a3": "Initial setup takes less than 30 minutes. Our onboarding team guides you through the entire process and helps customize the AI for your business.",
    "faq.q4": "Can I cancel anytime?",
    "faq.a4": "Absolutely! There are no long-term contracts. You can cancel, pause, or upgrade your plan anytime without penalties.",
    "faq.q5": "Does the AI replace human agents?",
    "faq.a5": "No! The AI handles initial conversations and lead qualification, freeing you to focus on closing deals. Important conversations are automatically transferred to you.",
    "faq.q6": "Do you offer a free trial?",
    "faq.a6": "Yes! We offer a 7-day free trial on all plans. No credit card required.",

    // CTA
    "cta.title": "Ready to get",
    "cta.titleHighlight": "started?",
    "cta.subtitle": "Join thousands of real estate professionals who never miss a lead with Alloha.",
    "cta.button": "Start free trial",
    "cta.note": "No credit card required • 7 days free • Cancel anytime",

    // Footer
    "footer.privacy": "Privacy",
    "footer.terms": "Terms",
    "footer.contact": "Contact",
    "footer.rights": "© 2026 Alloha. All rights reserved.",
  },
  "pt-BR": {
    // Navigation
    "nav.about": "Sobre",
    "nav.blog": "Blog",
    "nav.features": "Recursos",
    "nav.pricing": "Preços",
    "nav.faq": "FAQ",
    "nav.bookCall": "Testar grátis",

    // Hero
    "hero.urgency": "Corra, restam apenas",
    "hero.spotsLeft": "5 vagas.",
    "hero.title1": "O assistente ",
    "hero.titleHighlight": "Ilimitado",
    "hero.title2": "de verdade.",
    "hero.subtitle1": "Diga adeus aos leads perdidos e olá para respostas",
    "hero.subtitleHighlight": "ilimitadas",
    "hero.subtitle2": " e ultrarrápidas.",
    "hero.ctaPrimary": "Começar grátis",
    "hero.ctaSecondary": "Entrar para configurar",
    "hero.socialProof": "Nossos clientes são destaque em",

    // Phone Chat
    "phone.online": "Online 24/7",
    "phone.chat1": "Procuro um apartamento de 2 quartos em Curitiba",
    "phone.chat2": "Encontrei 12 opções perfeitas! 🏠",
    "phone.chat3": "Quer agendar visitas para amanhã?",
    "phone.chat4": "Sim! Às 14h seria perfeito 👍",
    "phone.placeholder": "Digite uma mensagem...",

    // Wave Chat Bubble
    "bubble.online": "Alloha AI • Online",
    "bubble.message": "Encontrei 3 apartamentos perfeitos no centro. Quer que eu agende visitas?",

    // Stats
    "stats.thisWeek": "Esta semana",
    "stats.leads": "+234 leads",
    "stats.vsLastWeek": "vs semana passada",

    // Testimonials
    "testimonial1.quote": "Alloha entrega leads bonitos e altamente convertidos em tempo recorde. É difícil encontrar uma solução melhor e Alloha conquistou isso. Ansioso para trabalhar no futuro.",
    "testimonial1.author": "Tony Soprano",
    "testimonial1.role": "CEO na ReMax",
    "testimonial2.quote": "Conseguir design era uma dor de cabeça. Estou tão feliz que encontramos Alloha. A IA é incrível, o trabalho é refrescantemente indolor.",
    "testimonial2.author": "Jenny Larkspur",
    "testimonial2.role": "Corretora de Imóveis",
    "testimonial3.quote": "A disponibilidade 24/7 foi um divisor de águas. Nunca mais perdemos um lead, mesmo às 3 da manhã. Nossa taxa de conversão dobrou.",
    "testimonial3.author": "Marcus Chen",
    "testimonial3.role": "Corretor na Keller Williams",

    // Process
    "process.label": "Processo",
    "process.title": "Seus leads,",
    "process.titleHighlight": "sem esforço.",
    "process.subtitle": "Comece sua jornada com IA em três passos simples.",
    "process.step1.title": "Assine",
    "process.step1.desc": "Assine um plano e solicite quantos designs quiser.",
    "process.step2.title": "Receba",
    "process.step2.desc": "Receba seu design em até dois dias úteis em média.",
    "process.step3.title": "Revise",
    "process.step3.desc": "Revisaremos os designs até você estar 100% satisfeito.",
    "process.cta": "Testar grátis por 7 dias",

    // Bento Grid
    "bento.visualize.title": "Visualize seus leads",
    "bento.visualize.desc": "Veja todas as conversas em um só painel",
    "bento.brand.title": "Encontre seus leads, domine sua marca",
    "bento.brand.desc": "IA personalizável que fala com a sua voz",
    "bento.multiplatform.title": "Colaboração Multiplataforma",
    "bento.multiplatform.desc": "Conecte com WhatsApp, Instagram, Website",
    "bento.mockups.title": "E-Mockups Disponíveis",
    "bento.mockups.desc": "Gere apresentações de imóveis instantaneamente",
    "bento.internet.title": "A Internet é sua tela",
    "bento.internet.desc": "Capture leads de qualquer fonte",

    // Benefits
    "benefits.label": "Benefícios",
    "benefits.title": "Rápido, qualidade",
    "benefits.titleHighlight": "e ilimitado.",
    "benefits.subtitle": "Alloha substitui respostas manuais não confiáveis por conversas impulsionadas por IA, entregues tão rápido que vai te surpreender.",
    "benefits.item1.title": "Envie Solicitações Ilimitadas",
    "benefits.item1.desc": "Envie quantas solicitações quiser e trabalharemos nelas uma por uma.",
    "benefits.item2.title": "Gerencie com Dashboard",
    "benefits.item2.desc": "Gerencie suas conversas usando o Dashboard. Visualize tarefas ativas, em fila e concluídas com facilidade.",
    "benefits.item3.title": "Pause Quando Quiser",
    "benefits.item3.desc": "Sem mais contratos! Apenas pause e retome sua assinatura em uma data futura.",
    "benefits.testimonial": "\"Conseguir design era uma dor de cabeça. Estou tão feliz que encontramos Alloha. O trabalho é incrivelmente refrescantemente indolor.\"",
    "benefits.testimonial.author": "Jenny Larkspur",
    "benefits.testimonial.role": "Corretora de Imóveis",

    // Features
    "features.label": "Recursos",
    "features.title": "Razões pelas quais você vai",
    "features.titleHighlight": "nos amar.",
    "features.subtitle": "Depois de experimentar Alloha, você nunca mais irá a outro lugar para IA. Sério.",
    "features.designBoard.title": "Quadro de Design",
    "features.designBoard.desc": "Solicite quantos designs quiser no seu próprio quadro.",
    "features.delivery.title": "Entrega Ultrarrápida",
    "features.delivery.desc": "Receba seus designs em 1-2 dias úteis.",
    "features.rate.title": "Taxa Mensal Fixa",
    "features.rate.desc": "Sem surpresas. Pague o mesmo preço fixo todo mês.",
    "features.designs.title": "Designs Premiados",
    "features.designs.desc": "Deixe seus clientes impressionados com designs premiados.",
    "features.revisions.title": "Revisões Ilimitadas",
    "features.revisions.desc": "Revise seus designs até estar 100% satisfeito. Sem limites.",
    "features.unique.title": "Único e Todo Seu",
    "features.unique.desc": "Todos os seus designs são criados especialmente para você.",
    "features.cta": "Testar grátis por 7 dias",

    // Solutions
    "solutions.label": "Soluções",
    "solutions.title": "Todas as suas",
    "solutions.titleHighlight": "necessidades",
    "solutions.title2": "cobertas.",
    "solutions.subtitle": "Administrar um negócio de sucesso significa mais do que apenas um site. Por isso cobrimos todas as suas necessidades imobiliárias.",
    "solutions.logos": "Logos",
    "solutions.landingPages": "Landing Pages",
    "solutions.websites": "Websites",
    "solutions.digitalProducts": "Produtos Digitais",
    "solutions.pitchDecks": "Pitch Decks",
    "solutions.mobileApps": "Apps Mobile",
    "solutions.emailDesign": "Design de Email",
    "solutions.productDesign": "Design de Produto",

    // Pricing
    "pricing.label": "Preços",
    "pricing.title": "Preços tão",
    "pricing.titleHighlight": "simples.",
    "pricing.subtitle": "Escolha o plano que se encaixa no seu negócio. Sem taxas escondidas, sem surpresas.",
    "pricing.mostPopular": "MAIS POPULAR",
    "pricing.starter.name": "Starter",
    "pricing.starter.price": "R$497",
    "pricing.starter.period": "/mês",
    "pricing.starter.desc": "Perfeito para corretores individuais",
    "pricing.starter.feature1": "1 número de WhatsApp",
    "pricing.starter.feature2": "500 conversas/mês",
    "pricing.starter.feature3": "Dashboard básico",
    "pricing.starter.feature4": "Suporte por email",
    "pricing.starter.feature5": "Respostas em até 5 segundos",
    "pricing.starter.cta": "Começar agora",
    "pricing.pro.name": "Professional",
    "pricing.pro.price": "R$197",
    "pricing.pro.period": "/mês",
    "pricing.pro.desc": "Ideal para imobiliárias em crescimento",
    "pricing.pro.feature1": "5 números de WhatsApp",
    "pricing.pro.feature2": "Conversas ilimitadas",
    "pricing.pro.feature3": "Dashboard avançado",
    "pricing.pro.feature4": "Suporte prioritário",
    "pricing.pro.feature5": "Integração CRM",
    "pricing.pro.feature6": "Relatórios personalizados",
    "pricing.pro.feature7": "Treinamento de IA customizado",
    "pricing.pro.cta": "Começar agora",
    "pricing.enterprise.name": "Enterprise",
    "pricing.enterprise.price": "Custom",
    "pricing.enterprise.period": "",
    "pricing.enterprise.desc": "Para grandes operações",
    "pricing.enterprise.feature1": "WhatsApp ilimitado",
    "pricing.enterprise.feature2": "API dedicada",
    "pricing.enterprise.feature3": "Gerente de conta",
    "pricing.enterprise.feature4": "SLA garantido",
    "pricing.enterprise.feature5": "Onboarding personalizado",
    "pricing.enterprise.feature6": "Integrações customizadas",
    "pricing.enterprise.cta": "Falar com vendas",
    "pricing.trial": "Testar grátis 7 dias",

    // FAQ
    "faq.label": "FAQ",
    "faq.title": "Perguntas",
    "faq.titleHighlight": "frequentes.",
    "faq.subtitle": "Tudo o que você precisa saber sobre Alloha.",
    "faq.q1": "Como funciona o Alloha?",
    "faq.a1": "Alloha é um assistente de IA que responde automaticamente às mensagens dos seus leads no WhatsApp, Instagram e site. Ele qualifica leads, agenda visitas e transfere conversas importantes para você.",
    "faq.q2": "Posso personalizar as respostas da IA?",
    "faq.a2": "Sim! Você pode treinar a IA com informações sobre seus imóveis, preços, localização e tom de voz da sua marca. A IA aprende e melhora continuamente.",
    "faq.q3": "Quanto tempo leva para configurar?",
    "faq.a3": "A configuração inicial leva menos de 30 minutos. Nosso time de onboarding te guia por todo o processo e ajuda a personalizar a IA para seu negócio.",
    "faq.q4": "Posso cancelar a qualquer momento?",
    "faq.a4": "Absolutamente! Não há contratos de longo prazo. Você pode cancelar, pausar ou fazer upgrade do seu plano a qualquer momento sem multas.",
    "faq.q5": "A IA substitui corretores humanos?",
    "faq.a5": "Não! A IA cuida das conversas iniciais e qualificação de leads, liberando você para focar em fechar negócios. Conversas importantes são transferidas para você automaticamente.",
    "faq.q6": "Vocês oferecem teste gratuito?",
    "faq.a6": "Sim! Oferecemos 7 dias de teste gratuito em todos os planos. Sem necessidade de cartão de crédito.",

    // CTA
    "cta.title": "Pronto para",
    "cta.titleHighlight": "começar?",
    "cta.subtitle": "Junte-se a milhares de profissionais imobiliários que nunca perdem um lead com Alloha.",
    "cta.button": "Iniciar teste grátis",
    "cta.note": "Sem cartão de crédito • 7 dias grátis • Cancele quando quiser",

    // Footer
    "footer.privacy": "Privacidade",
    "footer.terms": "Termos",
    "footer.contact": "Contato",
    "footer.rights": "© 2026 Alloha. Todos os direitos reservados.",
  },
};

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en");

  useEffect(() => {
    // Check localStorage for saved language preference
    const savedLang = localStorage.getItem("alloha-language") as Language;
    if (savedLang && (savedLang === "en" || savedLang === "pt-BR")) {
      setLanguageState(savedLang);
    } else {
      // Try to detect browser language
      const browserLang = navigator.language;
      if (browserLang.startsWith("pt")) {
        setLanguageState("pt-BR");
      }
    }
  }, []);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem("alloha-language", lang);
  };

  const t = (key: string): string => {
    return translations[language][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
