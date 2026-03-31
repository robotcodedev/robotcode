---
title: News
---

<script setup>
import { data as posts } from './posts.data'
import { useRouter } from 'vitepress'
import { onMounted } from 'vue'

const router = useRouter()

onMounted(() => {
  if (posts.length > 0) {
    router.go(posts[0].url)
  }
})
</script>

# News

Release announcements and news about RobotCode.

<div v-for="post of posts" :key="post.url" class="blog-post">
  <h2><a :href="post.url">{{ post.frontmatter.title }}</a></h2>
  <p class="blog-date">{{ new Date(post.frontmatter.date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) }}</p>
</div>

<style>
.blog-post {
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--vp-c-divider);
}
.blog-post:last-child {
  border-bottom: none;
}
.blog-post h2 {
  margin-top: 0;
  border-top: none;
}
.blog-date {
  color: var(--vp-c-text-2);
  font-size: 0.9rem;
}
</style>