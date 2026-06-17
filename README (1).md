```markdown
# 📋 A3 2.0 - Sistema de Gestão de Projetos e Equipes

[![Java](https://img.shields.io/badge/Java-21-orange.svg)](https://adoptium.net/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.2.0-brightgreen.svg)](https://spring.io/projects/spring-boot)

Sistema web completo para gerenciamento de projetos, equipes e tarefas com um quadro Kanban interativo. O projeto foi desenvolvido em **Java Spring Boot 3.2** utilizando o banco de dados **SQLite**, ideal para rodar localmente sem a necessidade de configurações complexas de servidores de banco de dados.

---

## ✨ Funcionalidades

- 🔐 **Autenticação e Autorização:** Sistema de login seguro utilizando Spring Security.
- 👥 **Gestão de Usuários:** Controle de perfis com permissões específicas (Administrador, Gerente e Colaborador).
- 📁 **Gestão de Projetos:** Criação e acompanhamento de projetos com controle de status, prazos e escopo.
- 🤝 **Gestão de Equipes:** Organização de times com definição de líderes e membros associados.
- 📋 **Quadro Kanban:** Interface visual e interativa para movimentação e acompanhamento de tarefas em tempo real.
- 💾 **Banco Embutido (SQLite):** Armazenamento simplificado em arquivo local, eliminando a necessidade de instalar um SGBD externo.

---

## 🛠️ Tecnologias Utilizadas

### Backend
* **Linguagem:** Java 21
* **Framework Principal:** Spring Boot 3.2.0
  * *Spring Web* (Construção da API e MVC)
  * *Spring Security* (Segurança e Controle de Acesso)
  * *Spring Data JPA* (Persistência de Dados)
  * *Spring Validation* (Validação de dados de entrada)
  * *Spring Thymeleaf* (Integração com o motor de templates)
* **Gerenciador de Dependências:** Maven
* **ORM:** Hibernate
* **Banco de Dados:** SQLite

### Frontend
* **Template Engine:** Thymeleaf
* **Framework CSS:** Bootstrap 5.3 + Bootstrap Icons
* **Linguagens Base:** HTML5 / CSS3 / JavaScript (ES6)

---

## 📂 Estrutura Simplificada do Projeto

```text
A3-2.0/
├── src/
│   ├── main/
│   │   ├── java/         # Código-fonte Java (Controllers, Services, Repositories, Models)
│   │   └── resources/
│   │       ├── static/   # Arquivos estáticos (CSS, JS, Imagens)
│   │       ├── templates/# Páginas HTML (Thymeleaf)
│   │       └── application.properties # Configurações do Spring e SQLite
└── pom.xml               # Dependências do Maven

```

---

## 🚀 Pré-requisitos

Antes de começar, você precisará ter instalado em sua máquina:

1. **Java Development Kit (JDK) 21** ou superior
* [Download do Eclipse Temurin (Adoptium)](https://adoptium.net/)
* Verifique a instalação: `java -version`


2. **Apache Maven 3.6+**
* [Download do Maven](https://maven.apache.org/download.cgi)
* Verifique a instalação: `mvn -version`


3. **Git** (Para clonar o repositório)
* [Download do Git](https://git-scm.com/)



---

## 📥 Instalação e Execução

### 1. Clonar o Repositório

```bash
git clone https://github.com/sunstrix/A3-2.0.git
cd A3-2.0

```

### 2. Configuração do Banco de Dados

O projeto já está configurado para criar automaticamente o arquivo do banco de dados SQLite (`a3_projeto.db` ou similar) na raiz do projeto assim que for iniciado pela primeira vez. Não é necessário executar scripts SQL externos.

### 3. Compilar e Rodar a Aplicação

Você pode rodar a aplicação diretamente pelo terminal utilizando o Maven:

```bash
# Limpar e compilar o projeto
mvn clean install

# Iniciar a aplicação
mvn spring-boot:run

```

A aplicação estará disponível no seu navegador através do endereço: **`http://localhost:8080`**

---

## 🤝 Como Contribuir

1. Faça um **Fork** do projeto.
2. Crie uma nova **Branch** para sua funcionalidade (`git checkout -b feature/NovaFuncionalidade`).
3. Faça o **Commit** de suas alterações (`git commit -m 'Adiciona nova funcionalidade'`).
4. Envie para o repositório remoto (`git push origin feature/NovaFuncionalidade`).
5. Abra um **Pull Request**.

```


```
