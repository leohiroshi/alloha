export type BlogCategory = "tutorials" | "tips" | "news";

export type BlogSection = {
  heading: string;
  paragraphs: string[];
};

export type BlogPost = {
  slug: string;
  title: string;
  excerpt: string;
  category: BlogCategory;
  categoryLabel: string;
  readTime: string;
  author: string;
  date: string;
  summary: string;
  thumbnail: string;
  thumbnailAlt: string;
  sections: BlogSection[];
};

export const blogPosts: BlogPost[] = [
  {
    slug: "como-estruturar-atendimento-imobiliario-com-ia",
    title: "Como estruturar atendimento imobiliário com IA",
    excerpt: "Desenhe um fluxo que responda rápido, qualifique melhor e mantenha o custo sob controle desde o primeiro MVP.",
    category: "tutorials",
    categoryLabel: "Tutoriais",
    readTime: "5 min",
    author: "Equipe Alloha",
    date: "2026-03-14",
    summary:
      "Atendimento com IA funciona melhor quando começa pelo essencial: captar lead, responder com clareza e devolver listagens relevantes. O custo permanece baixo quando o escopo também fica disciplinado.",
    thumbnail: "/blog/atendimento-imobiliario.svg",
    thumbnailAlt: "Capa preta e laranja sobre atendimento imobiliário com IA",
    sections: [
      {
        heading: "Comece pelo caminho de maior valor",
        paragraphs: [
          "Comece com o caminho de maior valor: captar lead, responder rápido e sugerir listagens relevantes. O objetivo não é parecer um atendente onisciente, e sim reduzir o tempo entre a intenção do cliente e a próxima ação útil.",
          "Quando o fluxo inicial está claro, fica mais fácil medir o que realmente melhora conversão. Sem esse recorte, a IA vira apenas uma camada cara em cima de um processo ainda confuso.",
        ],
      },
      {
        heading: "Proteja custo e capacidade",
        paragraphs: [
          "Mantenha limite de requests, hard-stop de capacidade e mensagens claras quando o modelo estiver indisponível. O produto fica mais confiável quando o limite é assumido com transparência.",
          "Com telemetria básica, você identifica gargalos sem elevar custo operacional. Esse aprendizado vale mais do que tentar cobrir todos os cenários logo no primeiro deploy.",
        ],
      },
    ],
  },
  {
    slug: "primeiro-mvp-sem-cron",
    title: "Primeiro MVP sem cron: como ativar rápido",
    excerpt: "Ative o produto, rode a primeira carga manual e valide a experiência antes de assumir jobs recorrentes.",
    category: "tips",
    categoryLabel: "Dicas",
    readTime: "4 min",
    author: "Equipe Alloha",
    date: "2026-03-12",
    summary:
      "No MVP inicial, a prioridade é validar o fluxo comercial com o menor custo operacional possível. Em vez de agendar automações recorrentes logo de cara, você executa a primeira carga no setup e confere a resposta real do produto.",
    thumbnail: "/blog/mvp-sem-cron.svg",
    thumbnailAlt: "Capa preta e laranja sobre MVP sem cron",
    sections: [
      {
        heading: "Por que evitar cron no início",
        paragraphs: [
          "No MVP inicial, o foco é velocidade de validação. Em vez de manter agendamentos recorrentes, você executa a primeira carga de imóveis no setup.",
          "Esse fluxo reduz custo fixo e simplifica a operação, mantendo o produto funcional para demonstração e primeiras vendas.",
        ],
      },
      {
        heading: "O que validar primeiro",
        paragraphs: [
          "A primeira pergunta não é se a infraestrutura está completa, e sim se o fluxo principal funciona de ponta a ponta.",
          "Quando o volume crescer, você pode evoluir para atualização orientada a evento ou jobs periódicos.",
        ],
      },
    ],
  },
  {
    slug: "checklist-antes-de-publicar",
    title: "Checklist antes de publicar em produção",
    excerpt: "Revise onboarding, documentos públicos, ambiente e conexões antes de abrir tráfego para clientes reais.",
    category: "tips",
    categoryLabel: "Dicas",
    readTime: "3 min",
    author: "Equipe Alloha",
    date: "2026-03-10",
    summary:
      "Publicar bem não depende só de deploy. Um MVP com boa aparência precisa ter onboarding claro, legal mínimo pronto e observabilidade suficiente para reagir a falhas.",
    thumbnail: "/blog/checklist-publicacao.svg",
    thumbnailAlt: "Capa preta e laranja com checklist de publicação",
    sections: [
      {
        heading: "Pontos obrigatórios",
        paragraphs: [
          "Valide onboarding, login, política de privacidade, termos e contato. Essas páginas fazem parte da confiança percebida pelo cliente e não podem parecer improvisadas.",
          "A consistência entre as páginas públicas reduz a sensação de produto inacabado e melhora a segurança de quem está avaliando a plataforma.",
        ],
      },
      {
        heading: "Antes do go-live",
        paragraphs: [
          "Confirme variáveis de ambiente, integração com Redis e status de conexão com banco.",
          "Monitore latência e erros dos endpoints principais antes de abrir tráfego.",
        ],
      },
    ],
  },
  {
    slug: "como-validar-a-busca-de-imoveis",
    title: "Como validar a busca de imóveis depois da primeira carga",
    excerpt: "Use consultas realistas para testar relevância, frescor dos dados e qualidade de retorno antes de vender escala.",
    category: "tutorials",
    categoryLabel: "Tutoriais",
    readTime: "6 min",
    author: "Hiroshi",
    date: "2026-03-08",
    summary:
      "A busca só está pronta quando responde como um usuário de verdade pesquisaria. Validar relevância, cobertura e clareza de resposta evita demonstrações bonitas com resultado fraco.",
    thumbnail: "/blog/busca-imoveis.svg",
    thumbnailAlt: "Capa preta e laranja sobre validação de busca de imóveis",
    sections: [
      {
        heading: "Teste como cliente final",
        paragraphs: [
          "Pesquise com frases como apartamento 2 quartos centro, casa com quintal ou studio para investimento. O objetivo é reproduzir o comportamento real de descoberta de um lead, não testar apenas IDs conhecidos.",
          "Quando o retorno responde com contexto, bairros e faixa de preço coerentes, a busca deixa de ser uma prova técnica e passa a apoiar venda de verdade.",
        ],
      },
      {
        heading: "Avalie sinais de qualidade",
        paragraphs: [
          "Olhe para a relevância dos primeiros resultados, a completude das informações e a velocidade de resposta. Esses três sinais contam mais do que um volume grande de resultados pouco úteis.",
          "Se houver ruído, ajuste dados, ranking ou o texto de resposta antes de ligar qualquer automação adicional.",
        ],
      },
    ],
  },
  {
    slug: "novo-fluxo-de-onboarding-do-mvp",
    title: "Novo fluxo de onboarding do MVP",
    excerpt: "O setup agora concentra configuração, primeira carga e validação de busca em uma jornada mais curta.",
    category: "news",
    categoryLabel: "Novidades",
    readTime: "4 min",
    author: "Equipe Alloha",
    date: "2026-03-06",
    summary:
      "O onboarding foi reorganizado para reduzir cliques e tirar etapas que só fariam sentido em uma operação mais madura. O foco agora é deixar o MVP rodando rápido.",
    thumbnail: "/blog/onboarding-mvp.svg",
    thumbnailAlt: "Capa preta e laranja sobre novo fluxo de onboarding do MVP",
    sections: [
      {
        heading: "Menos fricção na entrada",
        paragraphs: [
          "O novo fluxo reduz o número de decisões iniciais. Em vez de abrir muitas opções, ele concentra dados essenciais e empurra o usuário para a primeira validação do produto.",
          "Isso melhora a experiência de onboarding e reduz a chance de abandono logo nas primeiras telas.",
        ],
      },
      {
        heading: "Mais clareza sobre o próximo passo",
        paragraphs: [
          "Depois do login, o destino natural agora é o dashboard e, em seguida, o setup. Essa linearidade ajuda tanto quem está configurando quanto quem está demonstrando o produto para terceiros.",
          "O resultado é uma jornada que parece produto final, mesmo com escopo enxuto.",
        ],
      },
    ],
  },
  {
    slug: "sinais-de-que-o-mvp-esta-pronto-para-demo",
    title: "Sinais de que o MVP está pronto para uma boa demo",
    excerpt: "Nem sempre falta mais feature. Às vezes falta apenas consistência visual, narrativa clara e fluxo sem quebras.",
    category: "news",
    categoryLabel: "Novidades",
    readTime: "4 min",
    author: "Equipe Alloha",
    date: "2026-03-04",
    summary:
      "Um MVP bom de demo não depende de volume de features. Ele precisa parecer coeso, responder rápido e conduzir a pessoa por um caminho curto até o valor principal.",
    thumbnail: "/blog/demo-pronta.svg",
    thumbnailAlt: "Capa preta e laranja sobre sinais de que o MVP está pronto para demo",
    sections: [
      {
        heading: "Narrativa antes de profundidade",
        paragraphs: [
          "Se o usuário entende o valor do produto em poucos segundos, a demo já está na frente de muitas ferramentas mais completas. A narrativa precisa estar visível na home, no login, no setup e no dashboard.",
          "Quando cada tela aponta para a próxima, o MVP parece mais maduro do que de fato e, o mais importante, parece confiável.",
        ],
      },
      {
        heading: "Consistência e velocidade",
        paragraphs: [
          "Visual coeso, links funcionando e tempos de resposta previsíveis contam muito mais na percepção da demo do que menus extras ou páginas ainda vazias.",
          "Se o fluxo aguenta ser navegado sem explicação técnica a cada etapa, ele já está muito perto de uma boa apresentação comercial.",
        ],
      },
    ],
  },
];

export const blogCategoryLabels: Record<BlogCategory, string> = {
  tutorials: "Tutoriais",
  tips: "Dicas",
  news: "Novidades",
};

export function getBlogPostBySlug(slug: string) {
  return blogPosts.find((post) => post.slug === slug);
}
