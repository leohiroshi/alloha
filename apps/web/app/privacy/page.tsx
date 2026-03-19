import { LegalDocumentLayout } from "@/components/legal/LegalDocumentLayout";

const sections = [
  {
    id: "dados-coletados",
    title: "Dados coletados",
    paragraphs: [
      "Coletamos apenas os dados necessários para a operação da plataforma, como nome, telefone, e-mail, metadados de uso, informações técnicas de sessão e dados relacionados ao funcionamento das páginas, formulários e fluxos de atendimento.",
      "Em alguns casos, também podemos processar dados fornecidos pelo cliente durante a configuração, onboarding, captura de leads ou integrações habilitadas dentro do produto. O nível de coleta sempre busca acompanhar a menor superfície possível para o MVP.",
    ],
  },
  {
    id: "como-usamos",
    title: "Como usamos as informações",
    paragraphs: [
      "Os dados são utilizados para autenticar usuários, registrar sessões, responder mensagens, qualificar leads, executar buscas de listagens, acompanhar erros operacionais e melhorar a experiência geral do produto.",
      "Também podemos usar dados agregados ou técnicos para diagnóstico, segurança, observabilidade e evolução do serviço. Não usamos dados pessoais para fins incompatíveis com a operação principal informada ao cliente.",
    ],
  },
  {
    id: "compartilhamento",
    title: "Compartilhamento com terceiros",
    paragraphs: [
      "Não vendemos dados pessoais. O compartilhamento ocorre apenas com provedores técnicos, infraestrutura, autenticação, banco de dados, hospedagem, analytics ou operações estritamente necessárias para o funcionamento da plataforma.",
      "Sempre que um terceiro participar do processamento, a expectativa é que ele opere dentro de um papel técnico específico, com acesso limitado ao mínimo necessário para executar sua função.",
    ],
  },
  {
    id: "retencao-seguranca",
    title: "Retenção e segurança",
    paragraphs: [
      "Adotamos medidas técnicas e organizacionais para reduzir riscos de acesso não autorizado, uso indevido, alteração indevida ou perda acidental de dados. Nenhum sistema é absoluto, mas a arquitetura é configurada para minimizar exposições desnecessárias.",
      "Os dados são retidos pelo tempo necessário para operação, suporte, conformidade, investigação de incidentes ou obrigações legais aplicáveis. Quando a retenção deixa de ser necessária, o objetivo é remover ou anonimizar o que for possível.",
    ],
  },
  {
    id: "direitos",
    title: "Direitos do titular",
    paragraphs: [
      "Você pode solicitar acesso, correção, atualização ou exclusão de dados pessoais, respeitando limites técnicos, obrigações legais de retenção e necessidades legítimas de segurança ou auditoria.",
      "Se quiser exercer qualquer direito relacionado aos seus dados, utilize os canais de contato oficiais publicados no site. Sempre que possível, a resposta será dada em prazo razoável e com orientação objetiva sobre o próximo passo.",
    ],
  },
  {
    id: "alteracoes",
    title: "Alterações desta política",
    paragraphs: [
      "Esta política pode ser atualizada periodicamente para refletir evoluções do produto, ajustes de infraestrutura, mudanças legais ou aperfeiçoamento operacional. A versão publicada nesta página substitui versões anteriores.",
      "Quando a mudança for material para a forma como processamos dados, a intenção é tornar essa alteração perceptível dentro da experiência do produto ou nos canais usuais de comunicação.",
    ],
  },
];

export default function PrivacyPage() {
  return (
    <LegalDocumentLayout
      label="Legal"
      title="Política de Privacidade"
      version="Versão 1.0 - 14 de março de 2026"
      intro={[
        "Esta Política de Privacidade explica como a Alloha coleta, utiliza, compartilha e protege informações relacionadas ao uso da plataforma. O texto foi escrito para ser direto e funcional, com foco no contexto real deste MVP.",
        "A leitura desta página deve ajudar o cliente a entender o mínimo necessário sobre tratamento de dados, sem inflar o documento com linguagem vaga ou sem relação com a operação efetiva do produto.",
      ]}
      documentLinks={[
        { href: "/privacy", label: "Política de Privacidade", active: true },
        { href: "/terms", label: "Termos de Uso" },
        { href: "/contact", label: "Fale conosco" },
        { href: "/", label: "Voltar ao site" },
      ]}
      sections={sections}
    />
  );
}
