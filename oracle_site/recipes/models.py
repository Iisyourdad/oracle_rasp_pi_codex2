from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class HomePage(models.Model):
    title = models.CharField(max_length=200, default="Westbrook Recipes")
    background_image = models.ImageField(upload_to="backgrounds/", blank=True, null=True)

    def __str__(self):
        return self.title


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    background_image = models.ImageField(upload_to="backgrounds/", blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    UserProfile.objects.get_or_create(user=instance)

class Ingredient(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Recipe(models.Model):
    MEAL_TYPE_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('dessert', 'Dessert'),
    ]
    title = models.CharField(max_length=200)
    meal_type = models.CharField(max_length=10, choices=MEAL_TYPE_CHOICES, default='breakfast')
    instructions = models.TextField()
    ingredients = models.ManyToManyField(Ingredient)
    favorites = models.ManyToManyField(User, related_name='favorite_recipes', blank=True)

    def __str__(self):
        return self.title

class Instruction(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
