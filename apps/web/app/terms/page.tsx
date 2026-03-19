import { LegalDocumentLayout } from "@/components/legal/LegalDocumentLayout";

const sections = [
  {
    id: "aceitacao",
    title: "Aceitação",
    paragraphs: [
      "Ao utilizar a plataforma Alloha, você concorda com estes Termos de Uso e com as políticas relacionadas publicadas no site. Se estiver representando uma empresa, você declara que possui autorização para assumir esse compromisso em nome da operação.",
      "Caso não concorde com qualquer parte destes termos, o uso da plataforma deve ser interrompido. O acesso continuado ao produto após atualizações relevantes será interpretado como aceitação da versão vigente.",
    ],
  },
  {
    id: "definicoes",
    title: "Definições",
    paragraphs: [
      "Quando usamos os termos 'plataforma', 'serviço' ou 'produto', estamos nos referindo ao conjunto de páginas, integrações, interfaces, automações e componentes operados pela Alloha para atendimento imobiliário com IA.",
      "Quando usamos 'cliente' ou 'usuário', estamos nos referindo à pessoa física ou jurídica que utiliza a plataforma para configurar atendimento, capturar leads, gerenciar listagens ou validar o MVP em ambiente de operação.",
    ],
  },
  {
    id: "uso-permitido",
    title: "Licença e uso permitido",
    paragraphs: [
      "A Alloha concede ao cliente uma licença limitada, não exclusiva, revogável e intransferível para utilizar a plataforma conforme a finalidade contratada. Essa licença não transfere titularidade sobre software, interface, conteúdo técnico ou ativos de marca.",
      "O serviço deve ser usado apenas para operação legítima de atendimento, qualificação de leads e apresentação de listagens. Não é permitido utilizar a plataforma para atividades ilícitas, spam, coleta indevida de dados, scraping de terceiros sem autorização ou qualquer prática que viole contratos ou legislação aplicável.",
    ],
  },
  {
    id: "responsabilidades",
    title: "Responsabilidades do cliente",
    paragraphs: [
      "O cliente é responsável pelos dados informados na plataforma, pelo conteúdo publicado, pela origem das listagens utilizadas e pelo cumprimento das obrigações legais aplicáveis ao seu mercado e jurisdição.",
      "Também cabe ao cliente revisar fluxos, mensagens, textos públicos, configurações de onboarding e documentos legais antes da publicação. A plataforma ajuda a acelerar a operação, mas não substitui validação jurídica, comercial ou regulatória quando ela for necessária.",
    ],
  },
  {
    id: "disponibilidade",
    title: "Disponibilidade e limites",
    paragraphs: [
      "Buscamos manter a plataforma disponível e funcional, mas podem ocorrer indisponibilidades temporárias para manutenção, ajustes, atualizações, mudanças de provedores ou incidentes técnicos fora do controle da Alloha.",
      "Como este produto depende de infraestrutura e integrações de terceiros, algumas funções podem sofrer limites de capacidade, latência, hard-stop de quota ou indisponibilidade transitória. Sempre que possível, esses cenários serão tratados com mensagens claras dentro da experiência do produto.",
    ],
  },
  {
    id: "encerramento",
    title: "Suspensão e encerramento",
    paragraphs: [
      "A Alloha pode suspender ou encerrar o acesso em caso de uso indevido, violação destes termos, risco técnico relevante, tentativa de abuso da infraestrutura ou exigência legal. Sempre que viável, a medida será acompanhada de notificação prévia ou posterior com contexto mínimo do motivo.",
      "O cliente também pode interromper o uso da plataforma a qualquer momento. O encerramento do acesso não elimina obrigações anteriores nem afasta regras de retenção técnica, compliance ou investigação de incidentes quando elas forem exigidas.",
    ],
  },
];

export default function TermsPage() {
  return (
    <LegalDocumentLayout
      label="Legal"
      title="Termos de Uso"
      version="Versão 1.0 - 14 de março de 2026"
      intro={[
        "Estes Termos de Uso descrevem as regras para acesso e utilização da plataforma Alloha. O objetivo deste documento é deixar claro como o produto pode ser utilizado, quais responsabilidades continuam com o cliente e quais limites operacionais fazem parte deste primeiro MVP.",
        "Nós escrevemos este texto para ser direto. Ele não tenta transformar a página jurídica em uma área fria do site, mas também não abre mão de clareza sobre licença, responsabilidade, disponibilidade e encerramento de acesso.",
      ]}
      documentLinks={[
        { href: "/privacy", label: "Política de Privacidade" },
        { href: "/terms", label: "Termos de Uso", active: true },
        { href: "/contact", label: "Fale conosco" },
        { href: "/", label: "Voltar ao site" },
      ]}
      sections={sections}
    />
  );
}
