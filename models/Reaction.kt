package com.example.messenger.models

data class Reaction(
    val messageId: String,
    val emoji: String,
    val userId: Int
)
