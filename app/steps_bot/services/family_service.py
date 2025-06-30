from typing import List

from sqlalchemy import select, and_, func, delete, update
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.steps_bot.db.repo import get_session
from app.steps_bot.db.models.family import (
    Family,
    FamilyInvitation,
    FamilyInviteStatus,
)
from app.steps_bot.db.models.user import User


class FamilyService:
    @staticmethod
    async def get_family_info(telegram_id: int) -> tuple[Family | None, list[User]]:
        async with get_session() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if not user or not user.family_id:
                return None, []

            family = await session.get(Family, user.family_id)
            members = await session.scalars(
                select(User)
                .where(User.family_id == user.family_id)
                .order_by(User.id)
            )
            return family, list(members)

    @staticmethod
    async def create_family(telegram_id: int, name: str) -> Family:
        async with get_session() as session:
            owner = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if not owner:
                raise ValueError("owner not found")
            if owner.family_id:
                raise ValueError("already in family")

            dup = await session.scalar(select(Family).where(Family.name == name))
            if dup:
                raise ValueError("Семья с таким названием уже существует")

            family = Family(name=name)
            session.add(family)
            await session.flush()

            owner.family_id = family.id
            await session.flush()
            return family

    @staticmethod
    async def invite_user(
        inviter_tg: int,
        invitee_username: str,
    ) -> tuple[FamilyInvitation, str]:

        async with get_session() as session:
            inviter: User | None = await session.scalar(
                select(User)
                .options(selectinload(User.family))
                .where(User.telegram_id == inviter_tg)
            )
            if not inviter or not inviter.family:
                raise ValueError("Вы не можете пригласить данного")

            invitee: User | None = await session.scalar(
                select(User).where(User.username == invitee_username)
            )
            if not invitee:
                raise ValueError("Пользователь не найден")

            if invitee.family_id:
                raise ValueError("Пользователь уже состоит в семье")
            
            count_members = await session.scalar(
                select(func.count()).where(User.family_id == inviter.family_id)
            )
            if count_members >=5:
                raise ValueError("В семье уже 5 участников")

            exists = await session.scalar(
                select(FamilyInvitation).where(
                    and_(
                        FamilyInvitation.family_id == inviter.family_id,
                        FamilyInvitation.invitee_id == invitee.id,
                        FamilyInvitation.status == FamilyInviteStatus.PENDING,
                    )
                )
            )
            if exists:
                raise ValueError("invitation already sent")

            invitation = FamilyInvitation(
                family_id=inviter.family_id,
                inviter_id=inviter.id,
                invitee_id=invitee.id,
            )
            session.add(invitation)
            await session.flush()

            family_name = inviter.family.name
            return invitation, family_name

    @staticmethod
    async def respond_invitation(invitee_tg: int, inv_id: int, accept: bool) -> bool:
        """
        True -> приглашение принято, пользователь добавлен в семью  
        False -> приглашение отклонено и удалено
        """
        async with get_session() as session:
            inv = await session.get(FamilyInvitation, inv_id)
            if not inv or inv.status != FamilyInviteStatus.PENDING:
                raise ValueError("Приглашение не найдено или уже обработано")

            invitee = await session.scalar(
                select(User).where(User.telegram_id == invitee_tg)
            )
            if not invitee or invitee.id != inv.invitee_id:
                raise ValueError("Это приглашение не для вас")

            if accept:
                members_now = await session.scalar(
                    select(func.count()).where(User.family_id == inv.family_id)
                )
                if members_now >= 5:
                    raise ValueError("В семье уже 5 участников")
                
                inv.status = FamilyInviteStatus.ACCEPTED
                invitee.family_id = inv.family_id
                inv.responded_at = func.now()
                return True
            else:
                await session.delete(inv)
                return False

    @staticmethod
    async def leave_family(telegram_id: int):
        async with get_session() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if not user or not user.family_id:
                return

            fam_id = user.family_id
            user.family_id = None
            await session.flush()

            await session.execute(
                delete(FamilyInvitation).where(
                    FamilyInvitation.family_id == fam_id,
                    FamilyInvitation.invitee_id == user.id,
                )
            )

            members_left = await session.scalar(
                select(func.count()).where(User.family_id == fam_id)
            )
            if members_left == 0:
                fam = await session.get(Family, fam_id)
                await session.delete(fam)

    @staticmethod
    async def get_members(telegram_id: int) -> List[User]:
        async with get_session() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if not user or not user.family_id:
                return []

            result = await session.scalars(
                select(User).where(User.family_id == user.family_id)
            )
            return list(result)

    @staticmethod
    async def kick_member(owner_tg: int, member_db_id: int):
        async with get_session() as session:
            owner = await session.scalar(select(User).where(User.telegram_id == owner_tg))
            victim = await session.get(User, member_db_id)

            if not owner or not victim or owner.family_id != victim.family_id:
                raise ValueError("Не одна семья")

            real_owner_id = await session.scalar(
                select(User.id)
                .where(User.family_id == owner.family_id)
                .order_by(User.id)
                .limit(1)
            )
            if victim.id == real_owner_id:
                raise ValueError("Нельзя удалить владельца семьи")

            if victim.id == owner.id:
                raise ValueError("Нельзя удалить самого себя")

            victim.family_id = None

            await session.execute(
                delete(FamilyInvitation).where(
                    FamilyInvitation.family_id == owner.family_id,
                    FamilyInvitation.invitee_id == victim.id,
                )
            )
            
    @staticmethod
    async def get_invitation(inv_id: int) -> FamilyInvitation | None:
        async with get_session() as session:
            return await session.get(FamilyInvitation, inv_id)

    @staticmethod
    async def get_member_by_db_id(db_id: int) -> User | None:
        async with get_session() as session:
            return await session.get(User, db_id)
        
    @staticmethod
    async def disband_family(owner_tg: int):
        async with get_session() as session:
            owner = await session.scalar(
                select(User).where(User.telegram_id == owner_tg)
            )
            if not owner or not owner.family_id:
                raise ValueError("Вы не состоите в семье")

            fam_id = owner.family_id

            await session.execute(
                update(User)
                .where(User.family_id == fam_id)
                .values(family_id=None)
            )

            await session.execute(
                delete(FamilyInvitation).where(FamilyInvitation.family_id == fam_id)
            )

            fam = await session.get(Family, fam_id)
            await session.delete(fam)
            
    @staticmethod
    async def get_family_stats(telegram_id: int) -> tuple[Family | None, list[User], int, int, int, int]:
        async with get_session() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if not user or not user.family_id:
                return None, [], 0, 0, 0, 0

            family = await session.get(Family, user.family_id)

            members = list(
                await session.scalars(
                    select(User)
                    .where(User.family_id == user.family_id)
                    .order_by(User.id)
                )
            )

            total_steps   = sum(m.step_count for m in members)
            total_balance = sum(m.balance     for m in members)

            return (
                family,
                members,
                user.step_count,
                user.balance,
                total_steps,
                total_balance,
            )